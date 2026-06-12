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
from src.engine.prompts import SIMULATION_SUGGESTIONS_PROMPT
from google import genai
from google.genai import types

from src.utils.security import decrypt_key
from src.utils.common import check_authorization, get_user_data, get_authenticated_user
from src.database import UserConfig
from src.utils.limiter import limiter

# Quitamos el prefijo del router para evitar duplicidad con main.py
router = APIRouter(tags=["Simulation"])
logger = logging.getLogger(__name__)

class SimulationRequest(BaseModel):
    title: str
    hypothesis: str
    selected_ids: List[int] = Field(..., alias="selectedIds")
    api_key: Optional[str] = Field("", alias="apiKey")
    provider: str = "gemini" # gemini, mistral, hybrid
    mistral_key: Optional[str] = Field(None, alias="mistralKey")

    class Config:
        populate_by_name = True

async def process_simulation(sim_id: int, api_key: str, provider: str, mistral_key: Optional[str], selected_ids: List[int]):
    """Proceso de fondo para ejecutar el debate de agentes."""
    db = SessionLocal()
    try:
        logger.info("[Sim-%d] Iniciando simulación (%s)...", sim_id, provider)
        sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
        if not sim: return

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
        
        engine = SwarmEngine(api_key=api_key, provider=provider, mistral_key=mistral_key)
        
        async def on_message_callback(name, role, content, round_idx=1):
            with SessionLocal() as inner_db:
                agent = inner_db.query(SimulationAgent).filter(
                    SimulationAgent.simulation_id == sim_id, 
                    SimulationAgent.name == name
                ).first()
                if not agent:
                    agent = SimulationAgent(simulation_id=sim_id, name=name, role=role, description="Analista", personality="Profesional")
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

        report, history = await engine.run_simulation(sim.title, sim.hypothesis, session_data, on_message=on_message_callback)
        sim.result_report = report
        sim.status = "completed"
        db.commit()
    except Exception as e:
        logger.error("[Sim-%d] FALLO: %s", sim_id, type(e).__name__)
        if sim:
            sim.status = "error"
            sim.result_report = f"Error: {type(e).__name__}"
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
        if not api_key or len(api_key) < 10 or "..." in api_key:
            config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
            if config: api_key = decrypt_key(config.gemini_key)
        else:
            api_key = decrypt_key(api_key)

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
        
        background_tasks.add_task(
            process_simulation, 
            new_sim.id, 
            api_key, 
            req.provider, 
            req.mistral_key, 
            req.selected_ids
        )
        return {"status": "started", "simulation_id": new_sim.id}
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("Error al crear simulación: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error interno al iniciar la simulación.")

@router.get("/simulation/user/{user_id}")
async def list_simulations(user_id: str, db: Session = Depends(get_db)):
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
                    df = pd.read_csv(full_p_str, nrows=20) if full_p_str.endswith('.csv') else pd.read_excel(full_p_str, nrows=20)
                    if df is not None:
                        full_context_str += f"\nArchivo: {src.name}\nColumnas: {list(df.columns)}\n"
                        head_sample += f"\n--- {src.name} ---\n{df.head(15).to_string()}\n"
                except Exception as e:
                    logger.warning("[Sim-sugg] Error procesando %s: %s", final_path, type(e).__name__)
            else:
                logger.warning("[Sim-sugg] Archivo no encontrado: %s", src.name)

        if not full_context_str:
            return [{"title": "Sin contexto de datos", "hypothesis": "El sistema no pudo localizar físicamente los archivos seleccionados. Intenta subirlos de nuevo o verifica sus nombres."}]

        prompt = SIMULATION_SUGGESTIONS_PROMPT.format(context_str=full_context_str, head_str=head_sample)
        
        # [PILAR 2] Recuperar y Descifrar Key
        api_key = req.api_key
        if not api_key or len(api_key) < 10 or "..." in api_key:
            config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
            if config: api_key = decrypt_key(config.gemini_key)
        else:
            api_key = decrypt_key(api_key)

        prov = req.provider.lower()
        key = (req.mistral_key or api_key) if prov == "mistral" else api_key
        if prov == "hybrid": prov = "gemini"

        try:
            if prov == "mistral":
                from mistralai import Mistral
                m_client = Mistral(api_key=key)
                m_resp = m_client.chat.complete(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
                raw_text = m_resp.choices[0].message.content
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
            if isinstance(suggestions, dict) and "suggestions" in suggestions: suggestions = suggestions["suggestions"]
            return suggestions if isinstance(suggestions, list) else [suggestions]
        except Exception as e:
            logger.error("[Sim-sugg] Error en generación IA: %s", type(e).__name__)
            return [{"title": "Error en Motor IA", "hypothesis": "La IA no pudo procesar los datos. Verifica tu API key e intenta de nuevo."}]
    except Exception as e:
        logger.error("[Sim-sugg] Error crítico: %s", type(e).__name__)
        return [{"title": "Error Crítico", "hypothesis": "Error interno al procesar los archivos para el simulador."}]
