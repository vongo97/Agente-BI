import json
import pandas as pd
from typing import List, Dict, Callable, Optional
from google import genai
from google.genai import types
import asyncio
import random
import logging
from src.engine import prompts
from src.engine import skill_loader

logger = logging.getLogger(__name__)

class SwarmEngine:
    def __init__(self, api_key: str, provider: str = "gemini", mistral_key: Optional[str] = None, gemini_key: Optional[str] = None):
        self.api_key = api_key.strip() if api_key else ""
        self.mistral_key = (mistral_key or api_key or "").strip()
        self.gemini_key = (gemini_key or (api_key if provider == "gemini" else None) or "").strip()
        self.provider = provider.lower()
        
        # Modelos Gemini 3.x (Optimizado Capa Gratuita)
        self.gemini_model = "gemini-3-flash-preview"
        self.gemini_pro_model = "gemini-3.1-pro-preview"
        self.mistral_model = "mistral-small-latest"
        self.groq_model = "llama-3.3-70b-versatile"
        
        self.g_client = None
        self.m_client = None

        if self.provider in ["gemini", "hybrid"] or self.gemini_key:
            self.g_client = genai.Client(api_key=self.gemini_key if self.gemini_key else self.api_key)
            logger.info("[GEMINI] Motor activo: %s (clave de fallback cargada: %s)", self.gemini_model, bool(self.gemini_key))
            
        if self.provider in ["mistral", "hybrid"]:
            try:
                from mistralai import Mistral
                self.m_client = Mistral(api_key=self.mistral_key)
                logger.info("[MISTRAL] Motor activo: %s", self.mistral_model)
            except ImportError:
                logger.error("Librería mistralai no instalada.")

        if self.provider == "groq":
            logger.info("[GROQ] Motor activo: %s", self.groq_model)

    async def _generate_gemini(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        try:
            loop = asyncio.get_event_loop()
            config_args = {}
            if system_instruction:
                config_args["system_instruction"] = system_instruction
            response = await loop.run_in_executor(
                None,
                lambda: self.g_client.models.generate_content(
                    model=self.gemini_model, 
                    contents=prompt,
                    config=types.GenerateContentConfig(**config_args)
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"Error Gemini ({self.gemini_model}): {e}")
            return f"Error Gemini: {str(e)}"

    async def _generate_mistral(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        try:
            loop = asyncio.get_event_loop()
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})
            
            resp = await loop.run_in_executor(
                None, 
                lambda: self.m_client.chat.complete(
                    model=self.mistral_model,
                    messages=messages
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

    async def generate_agents(self, hypothesis: str, data_context: str) -> List[Dict]:
        """Genera perfiles de agentes dinámicos a partir de la hipótesis y el contexto de datos."""
        prompt = prompts.SWARM_PERSONA_PROMPT.format(
            context_str=data_context,
            head_str=data_context[:1000],
            agent_count=3,
            hypothesis=hypothesis
        )
        
        try:
            gen_func = self._generate_groq if self.provider == "groq" else self._generate_gemini
            system_instruction = skill_loader.get_system_prompt_for_agent("PLANNER")
            raw_json = await self._safe_generate(gen_func, prompt, wait_time=5, system_instruction=system_instruction)
            if raw_json:
                cleaned_json = raw_json.strip()
                if cleaned_json.startswith("```json"):
                    cleaned_json = cleaned_json[7:]
                if cleaned_json.endswith("```"):
                    cleaned_json = cleaned_json[:-3]
                cleaned_json = cleaned_json.strip()
                
                parsed = json.loads(cleaned_json)
                if isinstance(parsed, list) and len(parsed) > 0:
                    logger.info("[SwarmEngine] Agentes dinámicos generados con éxito: %s", [a.get('name') for a in parsed])
                    return parsed
        except Exception as e:
            logger.error("[SwarmEngine] Error al generar agentes dinámicos: %s. Usando fallback.", str(e))
            
        return [
            {"name": "Estratega", "role": "Analista Senior de Negocios", "description": "Estratégico e incisivo", "personality": "Estratégico"},
            {"name": "Analista", "role": "Data Scientist Senior", "description": "Riguroso y basado en evidencias", "personality": "Riguroso"},
            {"name": "Arquitecto", "role": "BI Solution Architect", "description": "Pragmático y visionario", "personality": "Pragmático"}
        ]

    async def run_simulation(self, title: str, hypothesis: str, session_data: Dict, on_message=None, num_rounds: int = 3, agents: Optional[List[Dict]] = None):
        data_context = self._get_data_context(session_data)
        
        # Si no se proporcionan agentes preconfigurados, los generamos dinámicamente
        if not agents:
            agents = await self.generate_agents(hypothesis, data_context)
        
        # Determinar qué motores ejecutar
        if self.provider == "hybrid":
            logger.debug("Iniciando DEBATE CRÚCE (Gemini + Mistral)...")
            report, history = await self._execute_hybrid_debate(hypothesis, data_context, agents, on_message, num_rounds)
            return report, history
        
        engine_name = "Gemini" if self.provider == "gemini" else ("Groq" if self.provider == "groq" else "Mistral")
        
        if self.provider == "gemini":
            generator_func = self._generate_gemini
        elif self.provider == "groq":
            generator_func = self._generate_groq
        else:
            generator_func = self._generate_mistral
        
        logger.debug("Iniciando debate con %s...", engine_name)
        report, history = await self._execute_debate(
            engine_name, 
            generator_func, 
            hypothesis, 
            data_context, 
            agents,
            on_message,
            num_rounds
        )
        return f"### Reporte de Simulación ({engine_name})\n{report}", history

    async def _execute_hybrid_debate(self, hypothesis: str, data_context: str, agents: List[Dict], on_message=None, num_rounds: int = 3):
        """Ejecuta un debate donde cada agente tiene un modelo distinto."""
        debate_history = []
        
        history_str = ""
        for round_idx in range(1, num_rounds + 1):
            for idx, agent in enumerate(agents):
                gen_func = self._generate_mistral if idx % 2 == 1 else self._generate_gemini
                model_label = "Mistral" if idx % 2 == 1 else "Gemini"
                agent_name_with_model = f"{agent['name']} ({model_label})"
                
                p = prompts.SWARM_AGENT_INTERACTION_PROMPT.format(
                    name=agent_name_with_model,
                    role=agent['role'],
                    personality=agent.get('personality', 'Profesional'),
                    description=agent.get('description', 'Analista'),
                    hypothesis=hypothesis,
                    round_number=round_idx,
                    history_str=history_str,
                    context_str=data_context
                )
                
                system_instruction = skill_loader.get_system_prompt_for_agent("SWARM_AGENT")
                content = await self._safe_generate(gen_func, p, system_instruction=system_instruction)
                
                if content and not content.startswith("Error"):
                    history_str += f"\n[{agent_name_with_model} - R{round_idx}]: {content}\n"
                    debate_history.append({"agent": agent_name_with_model, "content": content})
                    if on_message:
                         await on_message(
                            agent['name'], 
                            agent['role'], 
                            content, 
                            round_idx,
                            agent.get('description', 'Analista'),
                            agent.get('personality', 'Profesional')
                        )
                
                await asyncio.sleep(2 + random.uniform(0, 1))

        # Reporte final por Gemini Pro (el juez más potente) con espera agresiva
        synthesis_p = prompts.SWARM_REPORT_STRATEGIST_PROMPT.format(
            hypothesis=hypothesis,
            simulation_logs=history_str,
            context_str=data_context
        )
        strategist_system = skill_loader.get_system_prompt_for_agent("STRATEGIST")
        final_verdict = await self._safe_generate(self._generate_gemini_pro, synthesis_p, wait_time=15, system_instruction=strategist_system)
        
        # Fallback a Flash si el Pro falla (por cuotas o saturación)
        if not final_verdict or final_verdict.startswith("Error"):
            logger.warning("[SwarmEngine] Consolidación híbrida con Pro falló. Aplicando fallback inmediato a Flash.")
            final_verdict = await self._safe_generate(self._generate_gemini, synthesis_p, wait_time=5, system_instruction=strategist_system)
            
        if not final_verdict or final_verdict.startswith("Error"):
            final_verdict = "El estratega no pudo consolidar el reporte debido a saturación de la API. Por favor, intenta de nuevo o revisa los logs de los agentes."

        return f"### Veredicto Híbrido Consolidado (Gemini 3.1 Pro)\n{final_verdict}", debate_history

    async def _safe_generate(self, generator_func: Callable, prompt: str, wait_time: int = 5, system_instruction: Optional[str] = None):
        """Manejador seguro de peticiones con reintentos para rate limits."""
        attempts = 0
        while attempts < 3: # Aumentamos a 3 intentos
            content = await generator_func(prompt, system_instruction)
            if isinstance(content, str) and any(err in content for err in ["429", "RESOURCE_EXHAUSTED", "rate_limit", "Error"]):
                attempts += 1
                logger.debug("Reintento %d de IA tras %ds (rate limit).", attempts, wait_time)
                await asyncio.sleep(wait_time)
            else:
                return content
        return None

    async def _generate_gemini_pro(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Helper para usar específicamente el modelo Pro."""
        try:
            loop = asyncio.get_event_loop()
            config_args = {}
            if system_instruction:
                config_args["system_instruction"] = system_instruction
            response = await loop.run_in_executor(
                None,
                lambda: self.g_client.models.generate_content(
                    model=self.gemini_pro_model, 
                    contents=prompt,
                    config=types.GenerateContentConfig(**config_args)
                )
            )
            return response.text
        except Exception as e:
            return f"Error Gemini Pro: {str(e)}"

    async def _generate_groq(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Helper para usar el modelo Llama de Groq con fallback automático a Gemini."""
        try:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})
            
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                None,
                lambda: self._call_groq_api(self.groq_model, messages)
            )
            return content
        except Exception as e:
            logger.warning(f"[SwarmEngine] Groq falló ({self.groq_model}): {e}. Intentando fallback automático a Gemini...")
            if self.g_client:
                try:
                    return await self._generate_gemini(prompt, system_instruction)
                except Exception as gem_err:
                    logger.error(f"[SwarmEngine] Fallback a Gemini también falló: {gem_err}")
            return f"Error Groq: {str(e)}"

    def _call_groq_api(self, model: str, messages: list) -> str:
        import requests
        import time
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7
        }
        
        max_retries = 4
        delay = 2.0
        backoff_factor = 2.0
        
        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
            except Exception as e:
                err = str(e).lower()
                is_rate_limit = False
                if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
                    if e.response.status_code == 429:
                        is_rate_limit = True
                if "429" in err or "quota" in err or "exhausted" in err or "rate limit" in err:
                    is_rate_limit = True
                    
                if is_rate_limit and attempt < max_retries - 1:
                    logger.warning(
                        "[SwarmEngine] Rate limit alcanzado en Groq API (Intento %d/%d). Esperando %.1fs...",
                        attempt + 1, max_retries, delay
                    )
                    time.sleep(delay)
                    delay *= backoff_factor
                else:
                    raise e


    async def _execute_debate(self, engine_label: str, generator_func: Callable, hypothesis: str, data_context: str, agents: List[Dict], on_message=None, num_rounds: int = 3):
        debate_history = []
        
        history_str = ""
        for round_idx in range(1, num_rounds + 1):
            for agent in agents:
                agent_name_with_model = f"{agent['name']} ({engine_label})"
                
                p = prompts.SWARM_AGENT_INTERACTION_PROMPT.format(
                    name=agent_name_with_model,
                    role=agent['role'],
                    personality=agent.get('personality', 'Profesional'),
                    description=agent.get('description', 'Analista'),
                    hypothesis=hypothesis,
                    round_number=round_idx,
                    history_str=history_str,
                    context_str=data_context
                )
                
                system_instruction = skill_loader.get_system_prompt_for_agent("SWARM_AGENT")
                content = await self._safe_generate(generator_func, p, system_instruction=system_instruction)
                
                if content and not content.startswith("Error"):
                    history_str += f"\n[{agent_name_with_model} - R{round_idx}]: {content}\n"
                    debate_history.append({"agent": agent_name_with_model, "content": content})
                    if on_message:
                        await on_message(
                            agent['name'], 
                            agent['role'], 
                            content, 
                            round_idx,
                            agent.get('description', 'Analista'),
                            agent.get('personality', 'Profesional')
                        )
                
                await asyncio.sleep(2 + random.uniform(0, 1))

        synthesis_p = prompts.SWARM_REPORT_STRATEGIST_PROMPT.format(
            hypothesis=hypothesis,
            simulation_logs=history_str,
            context_str=data_context
        )
        
        strategist_system = skill_loader.get_system_prompt_for_agent("STRATEGIST")
        if engine_label == "Gemini":
            final_verdict = await self._safe_generate(self._generate_gemini_pro, synthesis_p, wait_time=15, system_instruction=strategist_system)
            # Fallback a Flash si el Pro falla (por cuotas o saturación)
            if not final_verdict or final_verdict.startswith("Error"):
                logger.warning("[SwarmEngine] Consolidación con Pro falló en debate Gemini. Aplicando fallback a Flash.")
                final_verdict = await self._safe_generate(self._generate_gemini, synthesis_p, wait_time=5, system_instruction=strategist_system)
        elif engine_label == "Groq":
            final_verdict = await self._safe_generate(self._generate_groq, synthesis_p, wait_time=5, system_instruction=strategist_system)
        else:
            final_verdict = await self._safe_generate(self._generate_mistral, synthesis_p, wait_time=15, system_instruction=strategist_system)
        
        if not final_verdict or final_verdict.startswith("Error"):
            final_verdict = "El estratega no pudo consolidar el reporte debido a saturación de la API."

        return final_verdict, debate_history
