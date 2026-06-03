import json
import pandas as pd
from typing import List, Dict, Callable, Optional
from google import genai
from google.genai import types
import asyncio
import random
import logging
from src.engine import prompts

logger = logging.getLogger(__name__)

class SwarmEngine:
    def __init__(self, api_key: str, provider: str = "gemini", mistral_key: Optional[str] = None):
        self.api_key = api_key.strip()
        self.mistral_key = (mistral_key or api_key).strip()
        self.provider = provider.lower()
        
        # Modelos Gemini 3.x (Optimizado Capa Gratuita)
        self.gemini_model = "gemini-3-flash-preview"
        self.gemini_pro_model = "gemini-3.1-pro-preview"
        self.mistral_model = "mistral-small-latest"
        
        self.g_client = None
        self.m_client = None

        if self.provider in ["gemini", "hybrid"]:
            self.g_client = genai.Client(api_key=self.api_key)
            logger.info("[GEMINI] Motor activo: %s", self.gemini_model)
            
        if self.provider in ["mistral", "hybrid"]:
            try:
                from mistralai import Mistral
                self.m_client = Mistral(api_key=self.mistral_key)
                logger.info("[MISTRAL] Motor activo: %s", self.mistral_model)
            except ImportError:
                logger.error("Librería mistralai no instalada.")

    async def _generate_gemini(self, prompt: str) -> str:
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.g_client.models.generate_content(model=self.gemini_model, contents=prompt)
            )
            return response.text
        except Exception as e:
            logger.error(f"Error Gemini ({self.gemini_model}): {e}")
            return f"Error Gemini: {str(e)}"

    async def _generate_mistral(self, prompt: str) -> str:
        try:
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, 
                lambda: self.m_client.chat.complete(
                    model=self.mistral_model,
                    messages=[{"role": "user", "content": prompt}]
                )
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.error(f"Error Mistral ({self.mistral_model}): {e}")
            return f"Error Mistral: {str(e)}"

    def _get_data_context(self, session_data: Dict) -> str:
        context_parts = []
        for name, df in session_data.items():
            if isinstance(df, pd.DataFrame):
                cols = df.columns.tolist()
                sample = df.head(3).to_dict(orient='records')
                context_parts.append(f"--- TABLA: {name} ---\nColumnas: {cols}\nMuestra: {json.dumps(sample)}")
        return "\n\n".join(context_parts)

    async def run_simulation(self, title: str, hypothesis: str, session_data: Dict, on_message=None):
        data_context = self._get_data_context(session_data)
        
        full_reports = []
        all_histories = []

        # Determinar qué motores ejecutar
        # Si es híbrido, hacemos un único debate cruzado
        if self.provider == "hybrid":
            logger.debug("Iniciando DEBATE CRÚCE (Gemini + Mistral)...")
            report, history = await self._execute_hybrid_debate(hypothesis, data_context, on_message)
            return report, history
        
        # Si es individual, mantenemos la lógica pero simplificada a una sola ejecución
        engine_name = "Gemini" if self.provider == "gemini" else "Mistral"
        generator_func = self._generate_gemini if self.provider == "gemini" else self._generate_mistral
        
        logger.debug("Iniciando debate con %s...", engine_name)
        report, history = await self._execute_debate(
            engine_name, 
            generator_func, 
            hypothesis, 
            data_context, 
            on_message
        )
        return f"### Reporte de Simulación ({engine_name})\n{report}", history

    async def _execute_hybrid_debate(self, hypothesis: str, data_context: str, on_message=None):
        """Ejecuta un debate donde cada agente tiene un modelo distinto."""
        debate_history = []
        agents = [
            {"name": "Estratega (Gemini)", "role": "Analista Senior", "personality": "Estratégico", "gen": self._generate_gemini},
            {"name": "Analista (Mistral)", "role": "Data Scientist", "personality": "Técnico y Riguroso", "gen": self._generate_mistral},
            {"name": "Arquitecto (Gemini)", "role": "Solution Architect", "personality": "Pragmático", "gen": self._generate_gemini}
        ]

        history_str = ""
        for round_idx in range(1, 4):
            for agent in agents:
                p = prompts.SWARM_AGENT_INTERACTION_PROMPT.format(
                    name=agent['name'],
                    role=agent['role'],
                    personality=agent['personality'],
                    description="Experto BI",
                    hypothesis=hypothesis,
                    round_number=round_idx,
                    history_str=history_str,
                    context_str=data_context
                )
                
                content = await self._safe_generate(agent['gen'], p)
                
                # SOLO guardar y notificar si no es un error
                if content and not content.startswith("Error"):
                    history_str += f"\n[{agent['name']} - R{round_idx}]: {content}\n"
                    debate_history.append({"agent": agent['name'], "content": content})
                    if on_message:
                        await on_message(agent['name'], agent['role'], content, round_idx)
                
                await asyncio.sleep(2 + random.uniform(0, 1))

        # Reporte final por Gemini Pro (el juez más potente) con espera agresiva
        synthesis_p = prompts.SWARM_REPORT_STRATEGIST_PROMPT.format(
            hypothesis=hypothesis,
            simulation_logs=history_str,
            context_str=data_context
        )
        final_verdict = await self._safe_generate(self._generate_gemini_pro, synthesis_p, wait_time=15)
        
        if not final_verdict or final_verdict.startswith("Error"):
            final_verdict = "El estratega no pudo consolidar el reporte debido a saturación de la API. Por favor, intenta de nuevo o revisa los logs de los agentes."

        return f"### Veredicto Híbrido Consolidado (Gemini 3.1 Pro)\n{final_verdict}", debate_history

    async def _safe_generate(self, generator_func: Callable, prompt: str, wait_time: int = 5):
        """Manejador seguro de peticiones con reintentos para rate limits."""
        attempts = 0
        while attempts < 3: # Aumentamos a 3 intentos
            content = await generator_func(prompt)
            if isinstance(content, str) and any(err in content for err in ["429", "RESOURCE_EXHAUSTED", "rate_limit", "Error"]):
                attempts += 1
                logger.debug("Reintento %d de IA tras %ds (rate limit).", attempts, wait_time)
                await asyncio.sleep(wait_time)
            else:
                return content
        return None

    async def _generate_gemini_pro(self, prompt: str) -> str:
        """Helper para usar específicamente el modelo Pro."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.g_client.models.generate_content(model=self.gemini_pro_model, contents=prompt)
            )
            return response.text
        except Exception as e:
            return f"Error Gemini Pro: {str(e)}"

    async def _execute_debate(self, engine_label: str, generator_func: Callable, hypothesis: str, data_context: str, on_message=None):
        debate_history = []
        agents = [
            {"name": f"Estratega ({engine_label})", "role": "Analista Senior de Negocios", "personality": "Estratégico e incisivo"},
            {"name": f"Analista ({engine_label})", "role": "Data Scientist Senior", "personality": "Riguroso y basado en evidencias"},
            {"name": f"Arquitecto ({engine_label})", "role": "BI Solution Architect", "personality": "Pragmático y visionario"}
        ]

        history_str = ""
        # 3 Rondas de debate solicitadas
        for round_idx in range(1, 4):
            for agent in agents:
                p = prompts.SWARM_AGENT_INTERACTION_PROMPT.format(
                    name=agent['name'],
                    role=agent['role'],
                    personality=agent['personality'],
                    description="Experto en Inteligencia de Negocios",
                    hypothesis=hypothesis,
                    round_number=round_idx,
                    history_str=history_str,
                    context_str=data_context
                )
                
                content = await self._safe_generate(generator_func, p)
                
                if content and not content.startswith("Error"):
                    history_str += f"\n[{agent['name']} - R{round_idx}]: {content}\n"
                    debate_history.append({"agent": agent['name'], "content": content})
                    if on_message:
                        await on_message(agent['name'], agent['role'], content, round_idx)
                
                await asyncio.sleep(2 + random.uniform(0, 1))

        synthesis_p = prompts.SWARM_REPORT_STRATEGIST_PROMPT.format(
            hypothesis=hypothesis,
            simulation_logs=history_str,
            context_str=data_context
        )
        
        if engine_label == "Gemini":
            final_verdict = await self._safe_generate(self._generate_gemini_pro, synthesis_p, wait_time=15)
        else:
            final_verdict = await self._safe_generate(self._generate_mistral, synthesis_p, wait_time=15)
        
        if not final_verdict or final_verdict.startswith("Error"):
            final_verdict = "El estratega no pudo consolidar el reporte debido a saturación de la API."

        return final_verdict, debate_history
