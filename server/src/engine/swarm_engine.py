import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from google import genai
from google.genai import types

# Compatibilidad con mistralai
try:
    from mistralai import Mistral
except ImportError:
    Mistral = None

from src.database import SessionLocal, Simulation, SimulationAgent, SimulationMessage, DataSource
from src.engine import prompts

logger = logging.getLogger(__name__)

# Configuración de Modelos para el Enjambre
MODELS = {
    "GEMINI": "gemini-3-flash-preview",
    "MISTRAL": "mistral-large-latest"
}

API_CALL_DELAY = 10  # Delay para evitar saturación
MAX_RETRIES = 2      

class SwarmEngine:
    def __init__(self, api_key: str, provider: str = "gemini", mistral_key: str = None):
        self.api_key = api_key.strip() if api_key else None
        self.mistral_key = mistral_key.strip() if mistral_key else None
        self.provider = provider # gemini, mistral o hybrid (en hybrid el debate es mixto)
        self.db = None
        
        # Clientes
        self.gemini_client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.mistral_client = Mistral(api_key=self.mistral_key) if (Mistral and self.mistral_key) else None

    async def _safe_generate(self, prompt, role="SIMULATION", temperature=0.7, force_provider=None):
        """Generación robusta con soporte para ambos proveedores."""
        # Determinar qué proveedor usar
        target_provider = force_provider or self.provider
        
        # Validar disponibilidad de llaves para el proveedor elegido
        if target_provider == "gemini" and not self.gemini_client:
             raise Exception("Configuración incompleta: No se encontró la API Key de Google/Gemini para este usuario.")
        
        if target_provider == "mistral" and not self.mistral_client:
             raise Exception("Configuración incompleta: No se encontró la API Key de Mistral para este usuario.")

        for attempt in range(MAX_RETRIES):
            try:
                if target_provider == "gemini" and self.gemini_client:
                    response = await asyncio.to_thread(
                        self.gemini_client.models.generate_content,
                        model=MODELS["GEMINI"],
                        contents=prompt,
                        config=types.GenerateContentConfig(temperature=temperature, max_output_tokens=2048)
                    )
                    await asyncio.sleep(API_CALL_DELAY)
                    return response.text
                
                elif target_provider == "mistral" and self.mistral_client:
                    response = await asyncio.to_thread(
                        self.mistral_client.chat.complete,
                        model=MODELS["MISTRAL"],
                        messages=[{"role": "user", "content": prompt}]
                    )
                    await asyncio.sleep(2) # Mistral es más generoso con el delay
                    return response.choices[0].message.content
                
                else:
                    raise Exception(f"Proveedor {target_provider} no configurado correctamente.")

            except Exception as e:
                err_str = str(e).lower()
                if "503" in err_str or "overloaded" in err_str or "demand" in err_str:
                    if target_provider == "gemini" and self.mistral_client:
                        logger.warning("Gemini saturado. Saltando a Mistral como backup...")
                        target_provider = "mistral"
                        continue
                
                if "429" in err_str or "quota" in err_str:
                    wait_time = 20 * (attempt + 1)
                    await asyncio.sleep(wait_time)
                    continue
                
                logger.error(f"Error en Simulación ({target_provider}): {e}")
                raise

        raise Exception(f"Error crítico: El modelo {target_provider} no responde tras reintentos.")

    async def run_simulation(self, simulation_id: int):
        self.db = SessionLocal()
        try:
            sim = self.db.query(Simulation).filter(Simulation.id == simulation_id).first()
            if not sim: return

            logger.info(f"🚀 [SWARM] Iniciando simulación #{simulation_id} con proveedor: {self.provider.upper()}")
            print(f"🚀 [SWARM] Iniciando simulación #{simulation_id} con proveedor: {self.provider.upper()}")
            
            sim.status = "running"
            self.db.commit()

            context_str, head_str = self._get_data_context(sim.user_id, sim.data_source_id)
            
            # 1. Generar Agentes
            await self._generate_agents(sim, context_str, head_str)
            
            # 2. Debate (Rondas)
            for round_num in range(1, 4):
                await self._run_debate_round(sim, round_num)

            # 3. Reporte Final
            await self._generate_final_report(sim, context_str)

            sim.status = "completed"
            self.db.commit()

        except Exception as e:
            logger.error(f"Fallo en Enjambre: {e}")
            sim = self.db.query(Simulation).filter(Simulation.id == simulation_id).first()
            if sim:
                sim.status = "error"
                sim.result_report = f"Error en Enjambre: {str(e)}"
                self.db.commit()
        finally:
            self.db.close()

    def _get_data_context(self, user_id: str, data_source_id: Optional[int]):
        import pandas as pd
        from src.utils.common import get_session_file
        
        # 1. Cargar el Pool de Sesión Completo (Prioridad)
        session_file = get_session_file(user_id)
        session_data = None
        if os.path.exists(session_file):
            try:
                session_data = pd.read_pickle(session_file)
            except Exception as e:
                logger.error(f"Error cargando pool en Swarm: {e}")

        # 2. Si no hay sesión o se pide una fuente específica, intentar cargarla
        if not session_data and data_source_id:
            source = self.db.query(DataSource).filter(DataSource.id == data_source_id).first()
            if source and source.url != "session_memory" and os.path.exists(source.url):
                try:
                    loaded = pd.read_pickle(source.url)
                    if isinstance(loaded, pd.DataFrame):
                        session_data = {"type": "file", "data": {source.name or "dataset_1": loaded}}
                    else:
                        session_data = loaded
                except: pass

        if not session_data:
            return "Sin datos activos en la sesión.", "N/A"

        try:
            # session_data puede ser un DataFrame (antiguo) o un dict con "data" (nuevo pool)
            if isinstance(session_data, pd.DataFrame):
                dfs = {"dataset_default": session_data}
            else:
                dfs = session_data.get("data", {})

            if not dfs:
                return "No hay tablas cargadas en el pool.", "N/A"

            c = [f"Tabla '{n}': {df.columns.tolist()}" for n, df in dfs.items() if isinstance(df, pd.DataFrame)]
            h = [f"Muestra '{n}':\n{df.head(2).to_string()}" for n, df in dfs.items() if isinstance(df, pd.DataFrame)]
            
            return "\n".join(c), "\n".join(h)
        except Exception as e:
            logger.error(f"Error parseando contexto de simulación: {e}")
            return "Error leyendo el pool de datos.", "N/A"

    async def _generate_agents(self, sim, context_str, head_str):
        prompt = prompts.SWARM_PERSONA_PROMPT.format(
            context_str=context_str, head_str=head_str, agent_count=5, hypothesis=sim.hypothesis
        )
        # Usamos el proveedor preferido para crear la facción
        text = await self._safe_generate(prompt)
        try:
            js = text.strip()
            if "```json" in js: js = js.split("```json")[1].split("```")[0].strip()
            for d in json.loads(js):
                self.db.add(SimulationAgent(
                    simulation_id=sim.id, name=d["name"], role=d["role"], 
                    description=d["description"], personality=d["personality"], stance=d["stance"]
                ))
            self.db.commit()
        except: raise ValueError("Error al parsear agentes. Formato JSON inválido.")

    async def _run_debate_round(self, sim, round_num):
        agents = self.db.query(SimulationAgent).filter(SimulationAgent.simulation_id == sim.id).all()
        for agent in agents:
            history = self.db.query(SimulationMessage).filter(SimulationMessage.simulation_id == sim.id).order_by(SimulationMessage.created_at.desc()).limit(5).all()
            h_str = "\n".join([f"{m.agent.name if m.agent else 'Narrador'}: {m.content}" for m in reversed(history)])
            prompt = prompts.SWARM_AGENT_INTERACTION_PROMPT.format(
                name=agent.name, role=agent.role, personality=agent.personality, 
                description=agent.description, hypothesis=sim.hypothesis, round_number=round_num, history_str=h_str
            )
            # En modo 'hybrid', alternamos proveedores para el debate si ambos están disponibles
            round_provider = None
            if self.provider == "hybrid" and self.gemini_client and self.mistral_client:
                round_provider = "gemini" if (agents.index(agent) + round_num) % 2 == 0 else "mistral"
            
            text = await self._safe_generate(prompt, temperature=0.8, force_provider=round_provider)
            self.db.add(SimulationMessage(
                simulation_id=sim.id, agent_id=agent.id, round_number=round_num, content=text.strip()
            ))
            self.db.commit()

    async def _generate_final_report(self, sim, context_str):
        msgs = self.db.query(SimulationMessage).filter(SimulationMessage.simulation_id == sim.id).all()
        logs = "\n".join([f"[{m.round_number}] {m.agent.name}: {m.content}" for m in msgs])
        prompt = prompts.SWARM_REPORT_STRATEGIST_PROMPT.format(hypothesis=sim.hypothesis, simulation_logs=logs, context_str=context_str)
        
        # Para el veredicto final, si el proveedor es hybrid, preferimos a Mistral por su estilo ejecutivo
        final_provider = "mistral" if (self.provider == "hybrid" and self.mistral_client) else self.provider
        
        text = await self._safe_generate(prompt, temperature=0.3, force_provider=final_provider)
        sim.result_report = text
        self.db.commit()
