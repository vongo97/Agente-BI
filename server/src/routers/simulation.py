from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
import os
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from src.database import get_db, Simulation, SimulationAgent, SimulationMessage, UserConfig
from src.engine.swarm_engine import SwarmEngine

router = APIRouter(tags=["Simulation"])

class SimulationCreate(BaseModel):
    user_id: str
    title: str
    hypothesis: str
    data_source_id: int | None = None
    api_key: str | None = None

class SimulationSchema(BaseModel):
    id: int
    user_id: str
    title: str
    hypothesis: str
    status: str
    result_report: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True

@router.post("/simulation", response_model=SimulationSchema)
async def create_simulation(
    sim_data: SimulationCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # 1. Crear registro de simulación
    db_sim = Simulation(
        user_id=sim_data.user_id,
        title=sim_data.title,
        hypothesis=sim_data.hypothesis,
        data_source_id=sim_data.data_source_id,
        status="pending"
    )
    db.add(db_sim)
    db.commit()
    db.refresh(db_sim)

    # 2. Obtener Configuración completa del usuario
    config = db.query(UserConfig).filter(UserConfig.user_id == sim_data.user_id).first()
    
    # Prioridades de API Keys: 1. Request Body, 2. DB Config, 3. Env Vars
    gemini_key = sim_data.api_key or (config.gemini_key if config else None) or os.getenv("GEMINI_API_KEY")
    mistral_key = (config.mistral_key if config else None) or os.getenv("MISTRAL_API_KEY")
    provider = (config.preferred_provider if config else "gemini") or "gemini"

    if not gemini_key and not mistral_key:
        db_sim.status = "error"
        db_sim.result_report = "No se encontraron API Keys configuradas (Gemini o Mistral)."
        db.commit()
        raise HTTPException(status_code=400, detail="Configura al menos una API Key en la barra lateral.")

    # Guardar qué proveedor se usó para esta simulación
    db_sim.provider = provider
    db.commit()

    # 3. Lanzar motor en segundo plano con soporte multi-modelo
    engine = SwarmEngine(api_key=gemini_key, provider=provider, mistral_key=mistral_key)
    background_tasks.add_task(engine.run_simulation, db_sim.id)

    return db_sim

@router.get("/simulation/user/{user_id}", response_model=List[SimulationSchema])
async def list_simulations(user_id: str, db: Session = Depends(get_db)):
    return db.query(Simulation).filter(Simulation.user_id == user_id).order_by(Simulation.created_at.desc()).all()

@router.get("/simulation/{sim_id}", response_model=SimulationSchema)
async def get_simulation(sim_id: int, db: Session = Depends(get_db)):
    sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")
    return sim

@router.get("/simulation/{sim_id}/messages")
async def get_simulation_messages(sim_id: int, db: Session = Depends(get_db)):
    messages = db.query(SimulationMessage).filter(
        SimulationMessage.simulation_id == sim_id
    ).order_by(SimulationMessage.created_at.asc()).all()
    
    return [
        {
            "id": m.id,
            "agent_name": m.agent.name if m.agent else "Narrador",
            "agent_role": m.agent.role if m.agent else "Sistema",
            "content": m.content,
            "round": m.round_number,
            "created_at": m.created_at
        } for m in messages
    ]

@router.post("/simulation/{sim_id}/retry")
async def retry_simulation(
    sim_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")
    
    # 1. Resetear estado y mensajes previos para empezar limpio
    sim.status = "pending"
    sim.result_report = None
    db.query(SimulationMessage).filter(SimulationMessage.simulation_id == sim_id).delete()
    db.query(SimulationAgent).filter(SimulationAgent.simulation_id == sim_id).delete()
    db.commit()

    # 2. Obtener llaves del usuario
    config = db.query(UserConfig).filter(UserConfig.user_id == sim.user_id).first()
    gemini_key = (config.gemini_key if config else None) or os.getenv("GEMINI_API_KEY")
    mistral_key = (config.mistral_key if config else None) or os.getenv("MISTRAL_API_KEY")
    provider = (config.preferred_provider if config else "gemini") or "gemini"

    # 3. Relanzar
    engine = SwarmEngine(api_key=gemini_key, provider=provider, mistral_key=mistral_key)
    background_tasks.add_task(engine.run_simulation, sim.id)

    return {"message": "Reintento de simulación iniciado", "status": "pending"}
