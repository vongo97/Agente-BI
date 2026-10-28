import asyncio
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

from src.utils.security import decrypt_key
from src.utils.common import check_authorization, get_user_data, get_authenticated_user
from src.database import UserConfig
from src.utils.limiter import limiter

# Quitamos el prefijo del router para evitar duplicidad con main.py
router = APIRouter(tags=["Simulation"])
logger = logging.getLogger(__name__)


async def _generate_simulation_json(
    *,
    provider: str,
    api_key: Optional[str],
    mistral_key: Optional[str],
    user_config,
    prompt: str,
    system_instruction: str,
    max_tokens: int,
) -> str:
    """Call the requested simulation provider; only hybrid has an explicit fallback."""
    from src.engine.providers import PROVIDERS, chat, get_model, resolve_keys

    selected = (provider or "gemini").strip().lower()
    if selected != "hybrid" and selected not in PROVIDERS:
        raise HTTPException(status_code=400, detail="El proveedor seleccionado no está disponible.")

    resolved_api_key, resolved_mistral_key, key_error = resolve_keys(
        selected, api_key, mistral_key, user_config
    )
    if selected == "hybrid":
        if not resolved_api_key or not resolved_mistral_key:
            raise HTTPException(
                status_code=400,
                detail="El modo híbrido requiere claves guardadas de Gemini y Mistral.",
            )
        providers = [("gemini", resolved_api_key), ("mistral", resolved_mistral_key)]
    else:
        if key_error:
            raise HTTPException(status_code=400, detail=key_error)
        key = resolved_mistral_key if selected == "mistral" else resolved_api_key
        if not key:
            raise HTTPException(status_code=400, detail="No hay una clave para el proveedor seleccionado.")
        providers = [(selected, key)]

    last_error: Optional[Exception] = None
    for index, (provider_id, key) in enumerate(providers):
        try:
            return await asyncio.to_thread(
                chat,
                provider=provider_id,
                key=key,
                prompt=prompt,
                temperature=0.1,
                system_instruction=system_instruction,
                timeout=30,
                model_override=get_model(provider_id, user_config),
                max_tokens=max_tokens,
            )
        except Exception as exc:
            last_error = exc
            if index < len(providers) - 1:
                logger.warning(
                    "Proveedor de simulación %s falló; usando fallback híbrido %s (%s)",
                    provider_id, providers[index + 1][0], type(exc).__name__,
                )

    logger.error(
        "Falló el proveedor de simulación seleccionado (%s): %s",
        selected, type(last_error).__name__ if last_error else "unknown",
    )
    raise HTTPException(
        status_code=502,
        detail="No se pudo generar la respuesta con el proveedor seleccionado.",
    )

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
            # La nube es la fuente de verdad: resuelve ruta local o descarga
            # el objeto desde Supabase a la caché local.
            from src.utils.common import resolve_source_path
            file_path = resolve_source_path(src)
            
            if file_path:
                df = None
                try:
                    from src.connectors.data_connectors import load_source_df
                    df = load_source_df(file_path, getattr(src, "is_encrypted", False), src.name)
                except Exception as e:
                    logger.warning("[Sim-%s] No se pudo cargar %s: %s", sim_id, src.name, type(e).__name__)
                if df is not None:
                    session_data[src.name] = df
            else:
                logger.warning(f"[Sim-{sim_id}] Archivo no encontrado en disco ni en nube: {src.name}")
        
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
            sim.result_report = "Error interno al ejecutar la simulación. Consulte los registros del servidor para más detalles."
            db.commit()
    finally:
        db.close()

@router.post("/simulation")
@limiter.limit("3/minute")
@limiter.limit("15/hour")
async def create_simulation(request: Request, req: SimulationRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    from src.utils.common import mask_email
    logger.info("Creando simulación %s para %s", req.provider, mask_email(authenticated_user))
    check_authorization(authenticated_user)
    
    try:
        # [P-04] La clave efectiva es SIEMPRE la del proveedor activo; la de Gemini
        # nunca se reutiliza para otro proveedor (hybrid = Gemini + Mistral).
        from src.engine.providers import resolve_keys
        config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
        api_key, mistral_key, key_error = resolve_keys(req.provider, req.api_key, req.mistral_key, config)
        if key_error and req.provider != "hybrid":
            raise HTTPException(status_code=400, detail=key_error)
            
        # Validación de claves antes de proceder
        if req.provider == "gemini" and not api_key:
            raise HTTPException(status_code=400, detail="Clave API de Gemini no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
        elif req.provider == "mistral" and not mistral_key:
            raise HTTPException(status_code=400, detail="Clave API de Mistral no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
        elif req.provider == "groq" and not api_key:
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
    except HTTPException:
        # P-43: una negativa deliberada (400/401/404) no es un fallo interno.
        raise
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
            # La nube es la fuente de verdad: resuelve ruta local o descarga
            # el objeto desde Supabase a la caché local.
            from src.utils.common import resolve_source_path
            resolved = resolve_source_path(src)
            final_path = Path(resolved) if resolved else None

            if final_path:
                try:
                    full_p_str = str(final_path.absolute())
                    from src.connectors.data_connectors import load_source_df
                    df = load_source_df(full_p_str, getattr(src, "is_encrypted", False), src.name, nrows=8)
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
        
        config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
        system_prompt = (
            "Eres un Socio Consultor de Gestión de Riesgos y Estrategia Corporativa de primer nivel. "
            "Propón hipótesis rigurosas y escenarios de estrés, con tono analítico y formal. "
            "Cíñete estrictamente a las reglas y datos provistos por el usuario y responde con JSON válido."
        )
        raw_text = await _generate_simulation_json(
            provider=req.provider,
            api_key=req.api_key,
            mistral_key=req.mistral_key,
            user_config=config,
            prompt=prompt,
            system_instruction=system_prompt,
            max_tokens=2048,
        )

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
                list_found = False
                for value in suggestions.values():
                    if isinstance(value, list):
                        suggestions = value
                        list_found = True
                        break
                if not list_found:
                    suggestions = [suggestions]

        final_suggestions = []
        if isinstance(suggestions, list):
            for item in suggestions:
                if isinstance(item, dict):
                    title_val = item.get("title") or item.get("titulo") or item.get("name") or item.get("nombre") or ""
                    hyp_val = item.get("hypothesis") or item.get("hipotesis") or item.get("description") or item.get("descripcion") or ""
                    if title_val or hyp_val:
                        final_suggestions.append({
                            "title": str(title_val).strip(),
                            "hypothesis": str(hyp_val).strip(),
                        })

        if not final_suggestions:
            raise HTTPException(status_code=502, detail="El proveedor devolvió sugerencias en un formato inválido.")
        return final_suggestions
    except HTTPException:
        # P-43: la validación de claves (400) debe llegar al cliente tal cual.
        raise
    except Exception as e:
        logger.exception("[Sim-sugg] Error crítico")
        raise HTTPException(status_code=500, detail="Error interno al procesar las sugerencias de simulación.")


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
            # La nube es la fuente de verdad: resuelve ruta local o descarga
            # el objeto desde Supabase a la caché local.
            from src.utils.common import resolve_source_path
            resolved = resolve_source_path(src)
            final_path = Path(resolved) if resolved else None

            if final_path:
                try:
                    full_p_str = str(final_path.absolute())
                    from src.connectors.data_connectors import load_source_df
                    df = load_source_df(full_p_str, getattr(src, "is_encrypted", False), src.name, nrows=20)
                    if df is not None:
                        full_context_str += f"\nArchivo: {src.name}\nColumnas: {list(df.columns)}\n"
                        head_sample += f"\n--- {src.name} ---\n{df.head(15).to_string()}\n"
                except Exception as e:
                    logger.warning("[Sim-ontology] Error procesando %s: %s", final_path, type(e).__name__)

        if not full_context_str:
            return {"nodes": [], "edges": []}

        prompt = SIMULATION_ONTOLOGY_PROMPT.format(context_str=full_context_str, head_str=head_sample)
        
        config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
        system_prompt = (
            "Eres un Diseñador y Arquitecto de Grafos de Conocimiento. "
            "Estructura una ontología analítica y formal y responde con JSON válido."
        )
        raw_text = await _generate_simulation_json(
            provider=req.provider or "groq",
            api_key=None,
            mistral_key=None,
            user_config=config,
            prompt=prompt,
            system_instruction=system_prompt,
            max_tokens=2048,
        )
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()

        ontology = json.loads(raw_text)
        if not isinstance(ontology, dict):
            raise HTTPException(status_code=502, detail="El proveedor devolvió una ontología inválida.")
        nodes = ontology.get("nodes", [])
        edges = ontology.get("edges", [])
        if not isinstance(nodes, list) or not isinstance(edges, list):
            raise HTTPException(status_code=502, detail="El proveedor devolvió una ontología inválida.")

        normalized_nodes = []
        seen_ids = set()
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_id = str(node.get("id") or node.get("id_nodo") or "").strip().lower()
            if node_id and node_id not in seen_ids:
                seen_ids.add(node_id)
                normalized_nodes.append({
                    "id": node_id,
                    "label": str(node.get("label") or node.get("nombre") or node.get("id") or "Entidad"),
                    "type": str(node.get("type") or node.get("tipo") or "Entity"),
                })

        normalized_edges = []
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            source = str(edge.get("source") or edge.get("origen") or "").strip().lower()
            target = str(edge.get("target") or edge.get("destino") or "").strip().lower()
            if source in seen_ids and target in seen_ids:
                normalized_edges.append({
                    "source": source,
                    "target": target,
                    "relationship": str(edge.get("relationship") or edge.get("relacion") or "relaciona"),
                })

        return {"nodes": normalized_nodes, "edges": normalized_edges}
    except HTTPException:
        # P-43: la validación de claves (400) debe llegar al cliente tal cual.
        raise
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("[Sim-ontology] Error crítico: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error interno al generar la ontología de simulación.")


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
            # La nube es la fuente de verdad: resuelve ruta local o descarga
            # el objeto desde Supabase a la caché local.
            from src.utils.common import resolve_source_path
            resolved = resolve_source_path(src)
            final_path = Path(resolved) if resolved else None

            if final_path:
                try:
                    full_p_str = str(final_path.absolute())
                    from src.connectors.data_connectors import load_source_df
                    df = load_source_df(full_p_str, getattr(src, "is_encrypted", False), src.name, nrows=20)
                    if df is not None:
                        full_context_str += f"\nArchivo: {src.name}\nColumnas: {list(df.columns)}\n"
                except Exception as e:
                    logger.warning("[Sim-agents] Error procesando %s: %s", final_path, type(e).__name__)

        # Si no hay contexto, usar una descripción básica
        data_context = full_context_str if full_context_str else "No hay archivos de datos específicos disponibles."

        # Recuperar y Descifrar Keys (P-04: cada proveedor usa SU propia clave).
        from src.engine.providers import resolve_keys
        config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()

        prov = req.provider.lower() if req.provider else "groq"

        key, mistral_key, key_error = resolve_keys(prov, req.api_key, req.mistral_key, config)
        if key_error and prov != "hybrid":
            raise HTTPException(status_code=400, detail=key_error)
        if prov == "hybrid":
            if not key:
                raise HTTPException(status_code=400, detail="Clave API de Gemini no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
            if not mistral_key:
                raise HTTPException(status_code=400, detail="Clave API de Mistral no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
        if prov == "mistral":
            key = mistral_key
        elif prov == "hybrid":
            prov = "gemini"

        # Clave de Gemini SOLO para el cliente de Gemini del enjambre (nunca para otro endpoint).
        gemini_key = key if prov == "gemini" else (resolve_keys("gemini", None, None, config)[0] or "")

        engine = SwarmEngine(api_key=key, provider=prov, mistral_key=mistral_key, gemini_key=gemini_key)
        agents = await engine.generate_agents(req.hypothesis, data_context)
        return agents
    except HTTPException:
        # P-43: la negativa accionable (400 por clave/validación) debe llegar al cliente.
        raise
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("[Sim-agents] Error al generar agentes: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error interno al generar agentes del debate.")

