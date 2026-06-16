import os
import json
import pandas as pd
from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Body, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging

# Los modelos y la base de datos están todos en database.py
from src.database import (
    get_db, 
    SessionLocal, 
    Simulation, 
    SimulationAgent, 
    SimulationMessage, 
    DataSource
)
from src.engine.swarm_engine import SwarmEngine
from src.engine.prompts import SIMULATION_SUGGESTIONS_PROMPT, SIMULATION_ONTOLOGY_PROMPT
from google import genai
from google.genai import types

from src.utils.security import decrypt_key
from src.utils.common import check_authorization, get_user_data, get_authenticated_user
from src.database import UserConfig
from src.utils.limiter import limiter

# Quitamos el prefijo del router para evitar duplicidad con main.py
router = APIRouter(tags=["Simulation"])
logger = logging.getLogger(__name__)

class SimulationAgentRequest(BaseModel):
    name: str
    role: str
    description: str
    personality: str

class SimulationRequest(BaseModel):
    title: str
    hypothesis: str
    selected_ids: List[int] = Field(..., alias="selectedIds")
    api_key: Optional[str] = Field("", alias="apiKey")
    provider: str = "gemini" # gemini, mistral, hybrid, groq
    mistral_key: Optional[str] = Field(None, alias="mistralKey")
    num_rounds: Optional[int] = Field(3, alias="numRounds")
    agents: Optional[List[SimulationAgentRequest]] = None

    class Config:
        populate_by_name = True

async def process_simulation(sim_id: int, api_key: str, provider: str, mistral_key: Optional[str], selected_ids: List[int], num_rounds: int = 3):
    """Proceso de fondo para ejecutar el debate de agentes."""
    db = SessionLocal()
    try:
        logger.info("[Sim-%d] Iniciando simulación (%s)... Rondas: %d", sim_id, provider, num_rounds)
        sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
        if not sim: return

        # Recuperar clave de Gemini para fallback de resiliencia
        gemini_key = None
        config = db.query(UserConfig).filter(UserConfig.user_id == sim.user_id).first()
        if config and config.gemini_key:
            gemini_key = decrypt_key(config.gemini_key)

        session_data = {}
        for src_id in selected_ids:
            src = db.query(DataSource).filter(DataSource.id == src_id, DataSource.user_id == sim.user_id).first()
            if not src:
                continue
            file_path = getattr(src, 'path', getattr(src, 'url', None))
            if not file_path:
                continue
            
            # Intentar recuperar de la nube si no existe localmente
            from src.utils.supabase_storage import sync_cloud_to_local
            sync_cloud_to_local(file_path)
            
            if os.path.exists(file_path):
                df = None
                try:
                    from src.connectors.data_connectors import load_file_data
                    df = load_file_data(file_path)
                except:
                    pass
                if df is not None:
                    session_data[src.name] = df
            else:
                logger.warning(f"[Sim-{sim_id}] Archivo no encontrado en disco ni en nube: {file_path}")
        
        # Cargar agentes guardados de la base de datos si existen
        db_agents = db.query(SimulationAgent).filter(SimulationAgent.simulation_id == sim_id).all()
        pre_agents = None
        if db_agents:
            pre_agents = [
                {
                    "name": a.name,
                    "role": a.role,
                    "description": a.description,
                    "personality": a.personality
                } for a in db_agents
            ]

        engine = SwarmEngine(api_key=api_key, provider=provider, mistral_key=mistral_key, gemini_key=gemini_key)
        
        async def on_message_callback(name, role, content, round_idx=1, description="Analista", personality="Profesional"):
            with SessionLocal() as inner_db:
                agent = inner_db.query(SimulationAgent).filter(
                    SimulationAgent.simulation_id == sim_id, 
                    SimulationAgent.name == name
                ).first()
                if not agent:
                    agent = SimulationAgent(
                        simulation_id=sim_id, 
                        name=name, 
                        role=role, 
                        description=description, 
                        personality=personality
                    )
                    inner_db.add(agent)
                    inner_db.commit()
                    inner_db.refresh(agent)
                
                msg = SimulationMessage(simulation_id=sim_id, agent_id=agent.id, content=content, round_number=round_idx)
                inner_db.add(msg)
                
                # Actualizar ronda actual en la simulación
                sim_obj = inner_db.query(Simulation).filter(Simulation.id == sim_id).first()
                if sim_obj:
                    sim_obj.current_round = round_idx
                
                inner_db.commit()

        report, history = await engine.run_simulation(sim.title, sim.hypothesis, session_data, on_message=on_message_callback, num_rounds=num_rounds, agents=pre_agents)
        sim.result_report = report
        sim.status = "completed"
        db.commit()
    except Exception as e:
        logger.exception("[Sim-%d] FALLO INESPERADO:", sim_id)
        if sim:
            sim.status = "error"
            sim.result_report = f"Error: {type(e).__name__} - {str(e)}"
            db.commit()
    finally:
        db.close()

@router.post("/simulation")
@limiter.limit("3/minute")
@limiter.limit("15/hour")
async def create_simulation(request: Request, req: SimulationRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    logger.info(f"Creando simulación {req.provider} para {authenticated_user}")
    check_authorization(authenticated_user)
    
    try:
        # [PILAR 2] Recuperar y Descifrar Key si es necesario
        api_key = req.api_key
        mistral_key = req.mistral_key
        
        if not api_key or len(api_key) < 10 or "..." in api_key:
            config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
            if config and config.gemini_key:
                api_key = decrypt_key(config.gemini_key)
        else:
            api_key = decrypt_key(api_key)
            
        if not mistral_key or len(mistral_key) < 10 or "..." in mistral_key:
            config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
            if config and config.mistral_key:
                mistral_key = decrypt_key(config.mistral_key)
        else:
            mistral_key = decrypt_key(mistral_key)
            
        # Validación de claves antes de proceder
        if req.provider == "gemini" and not api_key:
            raise HTTPException(status_code=400, detail="Clave API de Gemini no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
        elif req.provider == "mistral" and not mistral_key:
            raise HTTPException(status_code=400, detail="Clave API de Mistral no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
        elif req.provider == "groq":
            config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
            if config and config.groq_key:
                api_key = decrypt_key(config.groq_key)
            if not api_key:
                raise HTTPException(status_code=400, detail="Clave API de Groq no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
        elif req.provider == "hybrid":
            if not api_key:
                raise HTTPException(status_code=400, detail="Clave API de Gemini no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
            if not mistral_key:
                raise HTTPException(status_code=400, detail="Clave API de Mistral no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")

        new_sim = Simulation(
            user_id=authenticated_user, 
            title=req.title, 
            hypothesis=req.hypothesis, 
            status="running",
            provider=req.provider
        )
        db.add(new_sim)
        db.commit()
        db.refresh(new_sim)
        
        # Si el usuario configuró agentes explícitos, los guardamos en DB
        if req.agents:
            for ag in req.agents:
                db_agent = SimulationAgent(
                    simulation_id=new_sim.id,
                    name=ag.name,
                    role=ag.role,
                    description=ag.description,
                    personality=ag.personality
                )
                db.add(db_agent)
            db.commit()
        
        background_tasks.add_task(
            process_simulation, 
            new_sim.id, 
            api_key, 
            req.provider, 
            mistral_key, 
            req.selected_ids,
            req.num_rounds or 3
        )
        return {"status": "started", "simulation_id": new_sim.id}
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("Error al crear simulación: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error interno al iniciar la simulación.")

@router.get("/simulation")
@limiter.limit("15/minute")
async def list_simulations(request: Request, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    return db.query(Simulation).filter(Simulation.user_id == authenticated_user).order_by(Simulation.created_at.desc()).all()

@router.get("/simulation/{sim_id}")
async def get_simulation(sim_id: int, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    sim = db.query(Simulation).filter(Simulation.id == sim_id, Simulation.user_id == authenticated_user).first()
    if not sim: raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")
    return sim

@router.get("/simulation/{sim_id}/messages")
async def get_messages(sim_id: int, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    sim = db.query(Simulation).filter(Simulation.id == sim_id, Simulation.user_id == authenticated_user).first()
    if not sim: raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")
    
    msgs = db.query(SimulationMessage).filter(SimulationMessage.simulation_id == sim_id).all()
    result = []
    for m in msgs:
        agent = db.query(SimulationAgent).filter(SimulationAgent.id == m.agent_id).first()
        result.append({
            "id": m.id,
            "agent_name": agent.name if agent else "Sistema",
            "agent_role": agent.role if agent else "Asistente",
            "agent_description": agent.description if agent else "Analista",
            "agent_personality": agent.personality if agent else "Profesional",
            "content": m.content,
            "round_number": m.round_number,
            "created_at": m.created_at
        })
    return result

class SuggestionRequest(BaseModel):
    selected_ids: List[int] = Field(..., alias="selectedIds")
    api_key: Optional[str] = Field("", alias="apiKey")
    provider: str = "gemini"
    mistral_key: Optional[str] = Field(None, alias="mistralKey")

    class Config:
        populate_by_name = True

@router.post("/simulation/suggestions")
@limiter.limit("5/minute")
@limiter.limit("20/hour")
async def get_simulation_suggestions(request: Request, req: SuggestionRequest, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    if not req.selected_ids: return []
    try:
        sources = db.query(DataSource).filter(DataSource.id.in_(req.selected_ids), DataSource.user_id == authenticated_user).all()
        full_context_str = ""
        head_sample = ""
        from pathlib import Path
        for src in sources:
            file_path = getattr(src, 'path', getattr(src, 'url', None))
            if not file_path: continue
            
            p = Path(file_path)
            final_path = None
            
            # 0. Intentar recuperar de la nube si no existe localmente
            from src.utils.supabase_storage import sync_cloud_to_local
            sync_cloud_to_local(str(p))
            
            # 1. Intentar ruta absoluta/original
            if p.exists():
                final_path = p
            else:
                # 2. Intentar buscar en el directorio de trabajo (base del proyecto)
                local_p = Path(os.getcwd()) / p.name
                if local_p.exists():
                    final_path = local_p
                else:
                    # 3. Intentar buscar en las carpetas comunes incluyendo data_sources configurado
                    from src.utils.common import DATA_SOURCES_DIR
                    search_dirs = [
                        Path(DATA_SOURCES_DIR),
                        Path(os.getcwd()) / "uploads",
                        Path(os.getcwd()) / "server" / "uploads",
                        Path(os.getcwd()) / "data_sources",
                        Path(os.getcwd()) / "server" / "data_sources"
                    ]
                    
                    for s_dir in search_dirs:
                        candidate = s_dir / p.name
                        if candidate.exists():
                            final_path = candidate
                            break

            if final_path:
                try:
                    full_p_str = str(final_path.absolute())
                    df = pd.read_csv(full_p_str, nrows=8) if full_p_str.endswith('.csv') else pd.read_excel(full_p_str, nrows=8)
                    if df is not None:
                        full_context_str += f"\nArchivo: {src.name}\nColumnas: {list(df.columns)}\n"
                        head_sample += f"\n--- {src.name} ---\n{df.head(5).to_string()}\n"
                except Exception as e:
                    logger.warning("[Sim-sugg] Error procesando %s: %s", final_path, type(e).__name__)
            else:
                logger.warning("[Sim-sugg] Archivo no encontrado: %s", src.name)

        if not full_context_str:
            return [{"title": "Sin contexto de datos", "hypothesis": "El sistema no pudo localizar físicamente los archivos seleccionados. Intenta subirlos de nuevo o verifica sus nombres."}]

        prompt = SIMULATION_SUGGESTIONS_PROMPT.format(context_str=full_context_str, head_str=head_sample)
        
        # [PILAR 2] Recuperar y Descifrar Keys de forma independiente
        gemini_key = req.api_key
        mistral_key = req.mistral_key
        groq_key = None
        
        config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
        
        # Cargar y descifrar Gemini key
        if not gemini_key or len(gemini_key) < 10 or "..." in gemini_key:
            if config and config.gemini_key:
                gemini_key = decrypt_key(config.gemini_key)
        else:
            gemini_key = decrypt_key(gemini_key)
            
        # Cargar y descifrar Mistral key
        if not mistral_key or len(mistral_key) < 10 or "..." in mistral_key:
            if config and config.mistral_key:
                mistral_key = decrypt_key(config.mistral_key)
        else:
            if mistral_key:
                mistral_key = decrypt_key(mistral_key)
                
        # Cargar y descifrar Groq key
        if config and config.groq_key:
            groq_key = decrypt_key(config.groq_key)

        prov = req.provider.lower()
        
        # Validar la clave correspondiente al proveedor
        if prov == "gemini" and not gemini_key:
            raise HTTPException(status_code=400, detail="Clave API de Gemini no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
        elif prov == "mistral" and not mistral_key:
            raise HTTPException(status_code=400, detail="Clave API de Mistral no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
        elif prov == "groq" and not groq_key:
            raise HTTPException(status_code=400, detail="Clave API de Groq no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
        elif prov == "hybrid":
            if not gemini_key:
                raise HTTPException(status_code=400, detail="Clave API de Gemini no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
            if not mistral_key:
                raise HTTPException(status_code=400, detail="Clave API de Mistral no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
        
        key = mistral_key if prov == "mistral" else (groq_key if prov == "groq" else gemini_key)
        if prov == "hybrid": prov = "gemini"

        try:
            if prov == "mistral":
                from mistralai import Mistral
                m_client = Mistral(api_key=key)
                m_resp = m_client.chat.complete(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
                raw_text = m_resp.choices[0].message.content
            elif prov == "groq":
                try:
                    import requests
                    url = "https://api.groq.com/openai/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json"
                    }
                    system_prompt = (
                        "Eres un Socio Consultor de Gestión de Riesgos y Estrategia Corporativa de primer nivel. "
                        "Tu objetivo es proponer hipótesis de simulación y escenarios de estrés altamente rigurosos, "
                        "serios y de nivel directivo (C-Level). Tu tono debe ser extremadamente analítico, formal, "
                        "preciso y con máxima autoridad intelectual. Cíñete estrictamente a las reglas y datos provistos por el usuario."
                    )
                    payload = {
                        "model": "llama-3.3-70b-versatile",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"}
                    }
                    response = requests.post(url, json=payload, headers=headers, timeout=30)
                    response.raise_for_status()
                    result = response.json()
                    raw_text = result["choices"][0]["message"]["content"]
                except Exception as groq_err:
                    logger.warning("[Sim-sugg] Groq falló (ej: rate limit). Intentando fallback automático a Gemini... Error: %s", str(groq_err))
                    if gemini_key: # Si hay gemini_key de Gemini disponible, hacer fallback
                        client = genai.Client(api_key=gemini_key)
                        response = client.models.generate_content(
                            model="gemini-flash-latest", 
                            contents=prompt, 
                            config=types.GenerateContentConfig(response_mime_type="application/json")
                        )
                        raw_text = response.text.strip()
                    else:
                        raise groq_err
            else:
                client = genai.Client(api_key=key)
                # 'gemini-flash-latest' siempre apunta al mejor modelo flash estable disponible
                response = client.models.generate_content(
                    model="gemini-flash-latest", 
                    contents=prompt, 
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                raw_text = response.text.strip()
            
            # Limpiar posibles bloques de código markdown
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()
                
            suggestions = json.loads(raw_text)
            
            # Buscar la lista de sugerencias dentro de la respuesta si es un diccionario
            if isinstance(suggestions, dict):
                if "suggestions" in suggestions and isinstance(suggestions["suggestions"], list):
                    suggestions = suggestions["suggestions"]
                else:
                    # Intentar buscar cualquier clave que contenga una lista
                    list_found = False
                    for k, v in suggestions.items():
                        if isinstance(v, list):
                            suggestions = v
                            list_found = True
                            break
                    if not list_found:
                        # Si no hay ninguna lista interna, asumir que el objeto raíz representa una sola sugerencia
                        suggestions = [suggestions]
            
            # Asegurarnos de que sea una lista y normalizar las claves a "title" y "hypothesis"
            final_suggestions = []
            if isinstance(suggestions, list):
                for item in suggestions:
                    if isinstance(item, dict):
                        # Mapear "title" (español e inglés)
                        title_val = item.get("title") or item.get("titulo") or item.get("name") or item.get("nombre") or ""
                        # Mapear "hypothesis" (español e inglés)
                        hyp_val = item.get("hypothesis") or item.get("hipotesis") or item.get("description") or item.get("descripcion") or ""
                        
                        if title_val or hyp_val:
                            final_suggestions.append({
                                "title": str(title_val).strip(),
                                "hypothesis": str(hyp_val).strip()
                            })
            
            # Si tras la normalización la lista está vacía, envolver la respuesta original
            if not final_suggestions:
                final_suggestions = [{"title": "Sugerencia de Simulación", "hypothesis": str(suggestions)}]
                
            return final_suggestions
        except Exception as e:
            logger.exception("[Sim-sugg] Error en generación IA")
            return [{"title": "Error en Motor IA", "hypothesis": f"La IA no pudo procesar los datos. Detalles: {str(e)}"}]
    except Exception as e:
        logger.exception("[Sim-sugg] Error crítico")
        return [{"title": "Error Crítico", "hypothesis": f"Error interno al procesar los archivos para el simulador. Detalles: {str(e)}"}]


class OntologyRequest(BaseModel):
    selected_ids: List[int] = Field(..., alias="selectedIds")
    provider: Optional[str] = "groq"

    class Config:
        populate_by_name = True

@router.post("/simulation/ontology")
@limiter.limit("5/minute")
@limiter.limit("20/hour")
async def get_simulation_ontology(request: Request, req: OntologyRequest, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    if not req.selected_ids: 
        return {"nodes": [], "edges": []}
        
    try:
        sources = db.query(DataSource).filter(DataSource.id.in_(req.selected_ids), DataSource.user_id == authenticated_user).all()
        full_context_str = ""
        head_sample = ""
        from pathlib import Path
        for src in sources:
            file_path = getattr(src, 'path', getattr(src, 'url', None))
            if not file_path: continue
            
            p = Path(file_path)
            final_path = None
            
            # Recuperar de la nube si no existe localmente
            from src.utils.supabase_storage import sync_cloud_to_local
            sync_cloud_to_local(str(p))
            
            if p.exists():
                final_path = p
            else:
                local_p = Path(os.getcwd()) / p.name
                if local_p.exists():
                    final_path = local_p
                else:
                    from src.utils.common import DATA_SOURCES_DIR
                    search_dirs = [
                        Path(DATA_SOURCES_DIR),
                        Path(os.getcwd()) / "uploads",
                        Path(os.getcwd()) / "server" / "uploads",
                        Path(os.getcwd()) / "data_sources",
                        Path(os.getcwd()) / "server" / "data_sources"
                    ]
                    for s_dir in search_dirs:
                        candidate = s_dir / p.name
                        if candidate.exists():
                            final_path = candidate
                            break

            if final_path:
                try:
                    full_p_str = str(final_path.absolute())
                    df = pd.read_csv(full_p_str, nrows=20) if full_p_str.endswith('.csv') else pd.read_excel(full_p_str, nrows=20)
                    if df is not None:
                        full_context_str += f"\nArchivo: {src.name}\nColumnas: {list(df.columns)}\n"
                        head_sample += f"\n--- {src.name} ---\n{df.head(15).to_string()}\n"
                except Exception as e:
                    logger.warning("[Sim-ontology] Error procesando %s: %s", final_path, type(e).__name__)

        if not full_context_str:
            return {"nodes": [], "edges": []}

        prompt = SIMULATION_ONTOLOGY_PROMPT.format(context_str=full_context_str, head_str=head_sample)
        
        # Recuperar y Descifrar Keys de forma independiente
        config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
        prov = req.provider.lower() if req.provider else "groq"
        
        gemini_key = None
        if config and config.gemini_key:
            gemini_key = decrypt_key(config.gemini_key)
            
        mistral_key = None
        if config and config.mistral_key:
            mistral_key = decrypt_key(config.mistral_key)
            
        groq_key = None
        if config and config.groq_key:
            groq_key = decrypt_key(config.groq_key)

        # Validaciones de claves del proveedor seleccionado
        if prov == "gemini" and not gemini_key:
            raise HTTPException(status_code=400, detail="Clave API de Gemini no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
        elif prov == "mistral" and not mistral_key:
            raise HTTPException(status_code=400, detail="Clave API de Mistral no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
        elif prov == "groq" and not groq_key:
            raise HTTPException(status_code=400, detail="Clave API de Groq no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")

        try:
            if prov == "mistral":
                from mistralai import Mistral
                m_client = Mistral(api_key=mistral_key)
                m_resp = m_client.chat.complete(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
                raw_text = m_resp.choices[0].message.content
            elif prov == "groq":
                try:
                    import requests
                    url = "https://api.groq.com/openai/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {groq_key}",
                        "Content-Type": "application/json"
                    }
                    system_prompt = (
                        "Eres un Diseñador y Arquitecto de Grafos de Conocimiento Senior. "
                        "Tu objetivo es estructurar la ontología de los datos de forma analítica y formal. "
                        "Debes responder estrictamente en el formato JSON requerido."
                    )
                    payload = {
                        "model": "llama-3.3-70b-versatile",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"}
                    }
                    response = requests.post(url, json=payload, headers=headers, timeout=30)
                    response.raise_for_status()
                    result = response.json()
                    raw_text = result["choices"][0]["message"]["content"]
                except Exception as groq_err:
                    logger.warning("[Sim-ontology] Groq falló (ej: rate limit). Intentando fallback automático a Gemini... Error: %s", str(groq_err))
                    if gemini_key:
                        client = genai.Client(api_key=gemini_key)
                        response = client.models.generate_content(
                            model="gemini-flash-latest", 
                            contents=prompt, 
                            config=types.GenerateContentConfig(response_mime_type="application/json")
                        )
                        raw_text = response.text.strip()
                    else:
                        raise groq_err
            else:
                client = genai.Client(api_key=gemini_key)
                response = client.models.generate_content(
                    model="gemini-flash-latest", 
                    contents=prompt, 
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                raw_text = response.text.strip()
            
            # Limpiar
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()
                
            ontology = json.loads(raw_text)
            
            # Normalizar formato de salida
            nodes = ontology.get("nodes", [])
            edges = ontology.get("edges", [])
            
            # Asegurar IDs únicos y minúsculos para nodos
            normalized_nodes = []
            seen_ids = set()
            for n in nodes:
                if isinstance(n, dict):
                    n_id = str(n.get("id") or n.get("id_nodo") or "").strip().lower()
                    n_label = str(n.get("label") or n.get("nombre") or n.get("id") or "Entidad")
                    n_type = str(n.get("type") or n.get("tipo") or "Entity")
                    
                    if n_id and n_id not in seen_ids:
                        seen_ids.add(n_id)
                        normalized_nodes.append({
                            "id": n_id,
                            "label": n_label,
                            "type": n_type
                        })
            
            # Normalizar aristas
            normalized_edges = []
            for e in edges:
                if isinstance(e, dict):
                    source = str(e.get("source") or e.get("origen") or "").strip().lower()
                    target = str(e.get("target") or e.get("destino") or "").strip().lower()
                    rel = str(e.get("relationship") or e.get("relacion") or "relaciona")
                    
                    # Agregar solo si los nodos existen
                    if source in seen_ids and target in seen_ids:
                        normalized_edges.append({
                            "source": source,
                            "target": target,
                            "relationship": rel
                        })
            
            return {
                "nodes": normalized_nodes,
                "edges": normalized_edges
            }
        except Exception as e:
            logger.error("[Sim-ontology] Error en generación IA: %s", type(e).__name__)
            return {"nodes": [], "edges": []}
    except Exception as e:
        logger.error("[Sim-ontology] Error crítico: %s", type(e).__name__)
        return {"nodes": [], "edges": []}


class GenerateAgentsRequest(BaseModel):
    selected_ids: List[int] = Field(..., alias="selectedIds")
    hypothesis: str
    provider: Optional[str] = "groq"
    api_key: Optional[str] = Field("", alias="apiKey")
    mistral_key: Optional[str] = Field(None, alias="mistralKey")

    class Config:
        populate_by_name = True

@router.post("/simulation/generate-agents")
@limiter.limit("5/minute")
@limiter.limit("20/hour")
async def generate_agents_endpoint(request: Request, req: GenerateAgentsRequest, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    if not req.selected_ids:
        return []

    try:
        sources = db.query(DataSource).filter(DataSource.id.in_(req.selected_ids), DataSource.user_id == authenticated_user).all()
        full_context_str = ""
        from pathlib import Path
        for src in sources:
            file_path = getattr(src, 'path', getattr(src, 'url', None))
            if not file_path: continue
            
            p = Path(file_path)
            final_path = None
            
            from src.utils.supabase_storage import sync_cloud_to_local
            sync_cloud_to_local(str(p))
            
            if p.exists():
                final_path = p
            else:
                local_p = Path(os.getcwd()) / p.name
                if local_p.exists():
                    final_path = local_p
                else:
                    from src.utils.common import DATA_SOURCES_DIR
                    search_dirs = [
                        Path(DATA_SOURCES_DIR),
                        Path(os.getcwd()) / "uploads",
                        Path(os.getcwd()) / "server" / "uploads",
                        Path(os.getcwd()) / "data_sources",
                        Path(os.getcwd()) / "server" / "data_sources"
                    ]
                    for s_dir in search_dirs:
                        candidate = s_dir / p.name
                        if candidate.exists():
                            final_path = candidate
                            break

            if final_path:
                try:
                    full_p_str = str(final_path.absolute())
                    df = pd.read_csv(full_p_str, nrows=20) if full_p_str.endswith('.csv') else pd.read_excel(full_p_str, nrows=20)
                    if df is not None:
                        full_context_str += f"\nArchivo: {src.name}\nColumnas: {list(df.columns)}\n"
                except Exception as e:
                    logger.warning("[Sim-agents] Error procesando %s: %s", final_path, type(e).__name__)

        # Si no hay contexto, usar una descripción básica
        data_context = full_context_str if full_context_str else "No hay archivos de datos específicos disponibles."

        # Recuperar y Descifrar Keys de forma independiente
        gemini_key = req.api_key
        mistral_key = req.mistral_key
        groq_key = None
        
        config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
        
        if not gemini_key or len(gemini_key) < 10 or "..." in gemini_key:
            if config and config.gemini_key:
                gemini_key = decrypt_key(config.gemini_key)
        else:
            gemini_key = decrypt_key(gemini_key)
            
        if not mistral_key or len(mistral_key) < 10 or "..." in mistral_key:
            if config and config.mistral_key:
                mistral_key = decrypt_key(config.mistral_key)
        else:
            if mistral_key:
                mistral_key = decrypt_key(mistral_key)
                
        if config and config.groq_key:
            groq_key = decrypt_key(config.groq_key)

        prov = req.provider.lower() if req.provider else "groq"
        
        # Validar claves correspondientes
        if prov == "gemini" and not gemini_key:
            raise HTTPException(status_code=400, detail="Clave API de Gemini no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
        elif prov == "mistral" and not mistral_key:
            raise HTTPException(status_code=400, detail="Clave API de Mistral no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
        elif prov == "groq" and not groq_key:
            raise HTTPException(status_code=400, detail="Clave API de Groq no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
        elif prov == "hybrid":
            if not gemini_key:
                raise HTTPException(status_code=400, detail="Clave API de Gemini no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
            if not mistral_key:
                raise HTTPException(status_code=400, detail="Clave API de Mistral no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")

        key = mistral_key if prov == "mistral" else (groq_key if prov == "groq" else gemini_key)
        if prov == "hybrid": prov = "gemini"

        engine = SwarmEngine(api_key=key, provider=prov, mistral_key=mistral_key, gemini_key=gemini_key)
        agents = await engine.generate_agents(req.hypothesis, data_context)
        return agents
    except Exception as e:
        logger.error("[Sim-agents] Error al generar agentes: %s", type(e).__name__)
        raise HTTPException(status_code=500, detail="Error interno al generar agentes del debate.")

