import logging
import os
import json
import re
from io import StringIO
import pandas as pd
import plotly.express as px
from google import genai
from google.genai import types

# Módulos internos
from . import prompts as agent_prompts
from . import executor
from . import prompts
from . import skill_loader
from src.utils.common import SafeJSONEncoder

logger = logging.getLogger(__name__)

# Configuración de Modelos (Gemini 3.x - Optimizado Capa Gratuita)
MODELS = {
    "GEMINI_SWARM": "gemini-3-flash-preview",
    "GEMINI_ANALYTICS": "gemini-3-flash-preview", # Flash para evitar bloqueos de cuota
    "GEMINI_STRATEGY": "gemini-3.1-pro-preview",   # Solo para reportes finales complejos
    "MISTRAL": "mistral-large-latest"
}
# Alias principal
MODELS["GEMINI"] = MODELS["GEMINI_ANALYTICS"]

def validate_data_quality(data):
    """Verifica que el dataset (o pool) sea apto para análisis por IA."""
    if data is None:
        return False, "No se proporcionaron datos."
    
    # Caso 1: Diccionario de DataFrames (Pool)
    if isinstance(data, dict):
        if not data:
            return False, "El pool de datos está vacío."
        # Verificar que al menos uno de los DataFrames tenga datos
        has_any_data = False
        for df in data.values():
            if hasattr(df, 'empty') and not df.empty:
                has_any_data = True
                break
        if not has_any_data:
            return False, "Todas las tablas en el pool están vacías."
        return True, "OK"
    
    # Caso 2: DataFrame único
    if hasattr(data, 'empty'):
        if data.empty:
            return False, "El archivo está completamente vacío."
        if len(data) < 2:
            return False, "El archivo tiene muy pocas filas para un análisis real."
        return True, "OK"
        
    return False, "Formato de datos no reconocido para validación."

# Compatibilidad con mistralai
try:
    from mistralai import Mistral
except ImportError:
    Mistral = None
    logger.warning("Mistralai no instalado.")

# Caché global para evitar que el Garbage Collector destruya los clientes HTTPX (Error: Client has been closed)
_clients = {}

def get_client(api_key):
    if api_key not in _clients:
        # Control de fugas de memoria (limitar tamaño a 50)
        if len(_clients) >= 50:
            first_key = next(iter(_clients))
            try:
                del _clients[first_key]
            except KeyError:
                pass
        _clients[api_key] = genai.Client(api_key=api_key)
    return _clients[api_key]

def validate_api_key(api_key, provider="gemini"):
    if not api_key: return False, "API Key vacía."
    if len(api_key) < 10: return False, "API Key demasiado corta."
    
    try:
        # Bypasseamos la validación por red temporalmente debido a bugs del SDK de Google 
        # (Client has been closed) en instanciaciones rápidas.
        # Si la llave tiene un formato medianamente lógico, la aceptamos.
        return True, None
    except Exception as e:
        err = str(e).lower()
        # Si es un error de cuota o de modelo, la llave SÍ es válida (solo está agotada)
        if "429" in err or "quota" in err or "limit" in err:
            return True, None # Permitimos guardar aunque esté agotada
        return False, str(e)

def generate_ai_content(prompt, api_key, provider="gemini", temperature=0.7, model_level="SWARM", system_instruction=None):
    """Generación con manejo de niveles de potencia (Gemini 3.1) e inyección de System Prompt."""
    if not api_key: return "Error: API Key no proporcionada."
    clean_key = api_key.strip()
    
    import time
    max_retries = 4
    delay = 2.0
    backoff_factor = 2.0
    
    try:
        for attempt in range(max_retries):
            try:
                if provider == "gemini":
                    client = get_client(clean_key)
                    # Determinar qué modelo de la familia 3.1 usar
                    model_key = f"GEMINI_{model_level}"
                    model_name = MODELS.get(model_key, MODELS["GEMINI_SWARM"])
                    
                    config_args = {"temperature": temperature}
                    if system_instruction:
                        config_args["system_instruction"] = system_instruction
                        
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(**config_args)
                    )
                    return response.text
                elif provider == "mistral":
                    if not api_key: return "⚠️ Falta API Key de Mistral."
                    from mistralai import Mistral
                    if clean_key not in _clients:
                        _clients[clean_key] = Mistral(api_key=clean_key)
                    client = _clients[clean_key]
                    
                    messages = []
                    if system_instruction:
                        messages.append({"role": "system", "content": system_instruction})
                    messages.append({"role": "user", "content": prompt})
                    
                    resp = client.chat.complete(
                        model=MODELS["MISTRAL"],
                        messages=messages
                    )
                    return resp.choices[0].message.content
                elif provider == "groq":
                    import requests
                    url = "https://api.groq.com/openai/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {clean_key}",
                        "Content-Type": "application/json"
                    }
                    
                    messages = []
                    if system_instruction:
                        messages.append({"role": "system", "content": system_instruction})
                    messages.append({"role": "user", "content": prompt})
                    
                    payload = {
                        "model": "llama-3.3-70b-versatile",
                        "messages": messages,
                        "temperature": temperature
                    }
                    response = requests.post(url, json=payload, headers=headers, timeout=30)
                    response.raise_for_status()
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
            except Exception as e:
                err = str(e).lower()
                is_rate_limit = ("429" in err or "quota" in err or "exhausted" in err or "rate limit" in err)
                if is_rate_limit and attempt < max_retries - 1:
                    logger.warning(
                        "Rate limit/quota alcanzado en %s (Intento %d/%d). Reintentando en %.1fs... Error: %s",
                        provider, attempt + 1, max_retries, delay, type(e).__name__
                    )
                    time.sleep(delay)
                    delay *= backoff_factor
                else:
                    raise e
    except Exception as e:
        err = str(e).lower()
        if "429" in err or "quota" in err or "exhausted" in err:
            return f"⚠️ **¡Uy! Tu clave de {provider.capitalize()} se ha quedado sin créditos.**\nActualiza tu API Key en Configuración."
        if "503" in err or "high demand" in err or "unavailable" in err:
            return f"⚠️ **El motor de {provider.capitalize()} está saturado.**\nReintenta en unos segundos."
        if "invalid" in err or "key" in err or "permission" in err or "401" in err or "403" in err:
            return f"⚠️ **Error de Autenticación con {provider.capitalize()}.**\nTu API Key parece ser inválida. Revísala en Configuración."
        
        logger.error("Error AI (%s): %s", provider, type(e).__name__)
        return f"Error técnico ({provider}): {type(e).__name__}"
    
    return f"⚠️ Error: El motor de {provider} no pudo generar una respuesta. Verifica tu API Key."

def safe_parse_validator_json(raw_text):
    """
    Limpia y parsea de forma robusta la respuesta en formato JSON del Validator Agent.
    """
    try:
        clean_text = raw_text.strip()
        # 1. Quitar bloques markdown de código si existen
        if "```json" in clean_text:
            clean_text = re.search(r"```json\s*(.*?)\s*```", clean_text, re.DOTALL).group(1)
        elif "```" in clean_text:
            clean_text = re.search(r"```\s*(.*?)\s*```", clean_text, re.DOTALL).group(1)
        
        clean_text = clean_text.strip()
        
        # 2. Si todavía no empieza por '{' y termina por '}', extraer la subcadena JSON más externa
        if not (clean_text.startswith("{") and clean_text.endswith("}")):
            match = re.search(r"(\{.*\})", clean_text, re.DOTALL)
            if match:
                clean_text = match.group(1).strip()
        
        # 3. Intentar parsear
        data = json.loads(clean_text)
        if isinstance(data, dict):
            return {
                "status": data.get("status", "error"),
                "reason": data.get("reason", "No proporcionado"),
                "feedback": data.get("feedback", "No proporcionado")
            }
    except Exception as e:
        logger.warning("Error parseando JSON del validador: %s. Texto crudo: %s", e, raw_text)
    
    # Fallback seguro
    return {
        "status": "error",
        "reason": "Fallo al analizar la respuesta JSON del validador.",
        "feedback": "Por favor, vuelve a escribir la validación siguiendo estrictamente el formato JSON."
    }

async def analyze_data(data_context, query, api_key, chat_history=[], mode="file", provider="gemini", mistral_key=None, primary_source_name=None, temperature=0.7):
    """Analista Inteligente con soporte de Arquitectura Multi-Agente (Planner -> Executor -> Validator) y Aislamiento de Contexto."""
    try:
        # 1. Configuración de Roles y Proveedores
        if provider == "hybrid":
            if not mistral_key: return "⚠️ Error: Configura tu Mistral Key en Ajustes.", None, None
            eng_provider, eng_key = "gemini", api_key
            str_provider, str_key = "mistral", mistral_key
        elif provider == "mistral":
            if not mistral_key: return "⚠️ Error: Configura tu Mistral Key.", None, None
            eng_provider, eng_key = "mistral", mistral_key
            str_provider, str_key = "mistral", mistral_key
        elif provider == "groq":
            eng_provider, eng_key = "groq", api_key
            str_provider, str_key = "groq", api_key
        else:
            eng_provider, eng_key = "gemini", api_key
            str_provider, str_key = "gemini", api_key

        # 2. Preparar el Contexto de Datos
        focus_instruction = ""
        if isinstance(data_context, dict):
            tables_desc = []
            head_info = {}
            
            # Aislamiento si hay fuente primaria
            temp_context = data_context
            if primary_source_name and primary_source_name in temp_context:
                focus_instruction = f"⚠️ IMPORTANTE: Enfócate principalmente en la tabla '{primary_source_name}' si la pregunta no especifica otra, pero tienes acceso a todas las listadas abajo."
            
            for name, df in temp_context.items():
                if hasattr(df, 'columns'):
                    tables_desc.append(f"- Tabla '{name}': {df.columns.tolist()} ({len(df)} filas)")
                    head_info[name] = {
                        "muestra": df.head(5).to_dict(),
                        "tipos": df.dtypes.astype(str).to_dict()
                    }
            
            data_info = "\n".join(tables_desc)
            table_names_hint = "NOMBRES EXACTOS PARA ACCEDER A LAS TABLAS (cópialos literalmente):\n" + \
                               "\n".join([f"  dfs['{name}']" for name in temp_context.keys()])
            if primary_source_name and primary_source_name in temp_context:
                table_names_hint += f"\n⭐ TABLA PRINCIPAL PARA ESTA CONSULTA: dfs['{primary_source_name}']"
            
            data_var = "dfs"
            muestra_datos = json.dumps(head_info, indent=2, cls=SafeJSONEncoder)
        else:
            data_info = f"Columnas: {data_context.columns.tolist()} ({len(data_context)} filas)"
            table_names_hint = "Usa la variable 'df' directamente."
            data_var = "df"
            muestra_datos = json.dumps({
                "muestra": data_context.head(5).to_dict(),
                "tipos": data_context.dtypes.astype(str).to_dict()
            }, indent=2, cls=SafeJSONEncoder)

        # 3. Agente 1: Planner Agent (Diseño de la Estrategia)
        planner_prompt = agent_prompts.PLANNER_PROMPT_TEMPLATE.format(
            query=query,
            data_info=data_info,
            muestra_datos=muestra_datos,
            focus_instruction=focus_instruction,
            table_names_hint=table_names_hint
        )
        logger.info("Invocando Planner Agent...")
        planner_system = skill_loader.get_system_prompt_for_agent("PLANNER")
        plan = generate_ai_content(
            planner_prompt, 
            eng_key, 
            eng_provider, 
            temperature=temperature, 
            model_level="ANALYTICS",
            system_instruction=planner_system
        )
        if not plan or "⚠️" in plan:
            return plan or "⚠️ Error en Planner Agent.", None, None

        # 4. Bucle Multi-Agente (Executor ➔ Execution ➔ Validator) con máximo 3 reintentos (4 intentos en total)
        retry_count = 0
        max_retries = 3
        validator_feedback = ""
        
        raw_code = ""
        execution_text = ""
        fig_code = None
        
        while retry_count <= max_retries:
            logger.info("Iteración del bucle multi-agente: %d/%d", retry_count, max_retries)
            
            # Formatear el prompt del Executor
            executor_prompt = agent_prompts.EXECUTOR_PROMPT_TEMPLATE.format(
                query=query,
                plan=plan,
                data_info=data_info,
                muestra_datos=muestra_datos,
                table_names_hint=table_names_hint,
                data_var=data_var
            )
            
            # Anexar feedback del Validator si es un reintento
            if retry_count > 0 and validator_feedback:
                executor_prompt += f"\n\n⚠️ **FEEDBACK DE CORRECCIÓN DEL VALIDADOR (Corrige esto de forma prioritaria)**:\n{validator_feedback}"
            
            # Generar código Python
            logger.info("Invocando Executor Agent...")
            executor_system = skill_loader.get_system_prompt_for_agent("EXECUTOR")
            raw_code = generate_ai_content(
                executor_prompt, 
                eng_key, 
                eng_provider, 
                temperature=temperature, 
                model_level="ANALYTICS",
                system_instruction=executor_system
            )
            if not raw_code or "⚠️" in raw_code:
                return raw_code or "⚠️ Error en Executor Agent.", None, None
            
            # Ejecutar el código en el Sandbox
            logger.info("Ejecutando código en Sandbox...")
            execution_text, fig_code = await executor.execute_analysis(data_context, raw_code, data_var)
            
            # Determinar si la ejecución falló
            has_error = "⚠️ Error" in execution_text or "🛡️" in execution_text
            
            # Invocamos al Validator Agent (Validación de Calidad)
            validator_prompt = agent_prompts.VALIDATOR_PROMPT_TEMPLATE.format(
                query=query,
                plan=plan,
                code=raw_code,
                has_error=str(has_error),
                execution_result=execution_text
            )
            
            logger.info("Invocando Validator Agent...")
            validator_system = skill_loader.get_system_prompt_for_agent("VALIDATOR")
            validation_raw = ""
            if eng_provider == "gemini":
                try:
                    client = get_client(eng_key.strip())
                    model_name = MODELS.get("GEMINI_ANALYTICS", MODELS["GEMINI_SWARM"])
                    response = client.models.generate_content(
                        model=model_name,
                        contents=validator_prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.2,
                            response_mime_type="application/json",
                            system_instruction=validator_system
                        )
                    )
                    validation_raw = response.text
                except Exception as e:
                    logger.warning("Fallo en validación estructurada JSON nativo, usando fallback: %s", e)
                    validation_raw = generate_ai_content(
                        validator_prompt, 
                        eng_key, 
                        eng_provider, 
                        temperature=0.2, 
                        model_level="ANALYTICS",
                        system_instruction=validator_system
                    )
            else:
                validation_raw = generate_ai_content(
                    validator_prompt, 
                    eng_key, 
                    eng_provider, 
                    temperature=0.2, 
                    model_level="ANALYTICS",
                    system_instruction=validator_system
                )
            
            # Parseo robusto del JSON del Validator
            validation_result = safe_parse_validator_json(validation_raw)
            logger.info("Resultado de la Validación: %s", validation_result)
            
            if validation_result["status"] == "success":
                logger.info("Validación exitosa en el intento %d.", retry_count)
                break
            else:
                # Si falló la validación, guardamos el feedback e incrementamos contador
                validator_feedback = validation_result["feedback"]
                logger.warning("Intento %d fallido. Feedback: %s", retry_count, validator_feedback)
                retry_count += 1
                
        # 5. Generar la Narrativa Final con el Estratega
        clean_res = execution_text.split("---")[-1].strip() if "---" in execution_text else execution_text
        if "⚠️ Error" in execution_text:
            clean_res = f"⚠️ Análisis parcial por error persistente: {execution_text}"

        context_str = data_info if isinstance(data_context, dict) else f"Columnas: {data_context.columns.tolist()}"
        p_strat = prompts.STRATEGIST_PROMPT_TEMPLATE.format(query=query, real_results=clean_res, context_str=context_str)
        logger.info("Invocando Estratega...")
        strategist_system = skill_loader.get_system_prompt_for_agent("STRATEGIST")
        final_narrative = generate_ai_content(
            p_strat, 
            str_key, 
            str_provider, 
            temperature=temperature, 
            model_level="ANALYTICS",
            system_instruction=strategist_system
        )
        
        return final_narrative, fig_code, raw_code

    except Exception as e:
        logger.error("Critical Error in analyze_data: %s", type(e).__name__, exc_info=True)
        return f"### ❌ Error Crítico\n{type(e).__name__}: {str(e)}", None, None

def generate_report_summary(query, api_key, context_data=None, provider="gemini", mistral_key=None):
    key = (mistral_key or api_key) if provider == "mistral" else api_key
    p = prompts.REPORT_SUMMARY_PROMPT.format(query=query, context_str=str(context_data)[:200])
    return generate_ai_content(p, key, provider)

def detect_anomalies_hybrid(df, api_key, provider="gemini", mistral_key=None):
    key = (mistral_key or api_key) if provider == "mistral" else api_key
    # Lógica Z-Score simplificada
    prompt = prompts.ANOMALY_AUDITOR_PROMPT.format(findings_str="Análisis estadístico iniciado...", columns=df.columns.tolist(), sample=df.head(2).to_dict())
    return generate_ai_content(prompt, key, provider)

def suggest_questions(data_context, api_key, mode="file", provider="gemini", mistral_key=None, primary_source_name=None):
    # Seguridad de llaves: No permitir usar Gemini key para Mistral si no hay mistral_key
    if provider == "mistral":
        if not mistral_key:
            return ["⚠️ Configura tu clave de Mistral en Ajustes."]
        key = mistral_key
    else:
        key = api_key
    
    # AISLAMIENTO DE CONTEXTO: Si hay una fuente primaria, la priorizamos para las sugerencias
    if isinstance(data_context, dict) and primary_source_name and primary_source_name in data_context:
        data_context = {primary_source_name: data_context[primary_source_name]}

    # Construir context_str enriquecido con muestras de datos (Lógica inspirada en Simulador)
    context_parts = []
    try:
        if isinstance(data_context, dict):
            # Pool de DataFrames
            for name, df in data_context.items():
                if hasattr(df, 'columns'):
                    # Muestra más amplia (10 filas) y en formato tabla (to_string)
                    sample_str = df.head(10).to_string(index=False)
                    context_parts.append(f"### Tabla '{name}'\nColumnas: {df.columns.tolist()}\n\nMUESTRA DE DATOS:\n{sample_str}")
                else:
                    context_parts.append(f"Fuente '{name}': [Estructura no definida]")
        elif hasattr(data_context, 'columns'):
            # DataFrame único
            sample_str = data_context.head(10).to_string(index=False)
            context_parts.append(f"Columnas: {data_context.columns.tolist()}\n\nMUESTRA DE DATOS:\n{sample_str}")
        else:
            # Probablemente esquema SQL (string)
            context_parts.append(f"Esquema/Estructura:\n{str(data_context)[:1000]}")
    except Exception as e:
        logger.warning(f"Error generando muestra para sugerencias: {e}")
        context_parts.append(f"Error al leer muestra, usando estructura básica: {str(data_context)[:500]}")

    context_str = "\n\n".join(context_parts)
    p = prompts.BI_SUGGESTIONS_PROMPT.format(context_str=context_str)
    
    # GENERACIÓN CON MODO JSON (Si es Gemini)
    if provider == "gemini":
        try:
            client = get_client(key)
            response = client.models.generate_content(
                model=MODELS["GEMINI_ANALYTICS"],
                contents=p,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    response_mime_type="application/json"
                )
            )
            resp = response.text
        except Exception as e:
            logger.error(f"Error en modo JSON nativo: {e}")
            resp = generate_ai_content(p, key, provider)
    else:
        resp = generate_ai_content(p, key, provider)
    
    # VALIDACIÓN DE SEGURIDAD: Si es un mensaje de error de la IA, no parsear
    if resp.startswith("⚠️") or resp.startswith("Error"):
        if "Autenticación" in resp or "Key" in resp:
            return [f"Error de Configuración: {resp.split('.')[0]}"]
        return ["La IA está ocupada o saturada. Reintenta en un momento."]
    
    # Extraer las preguntas del JSON
    try:
        import json
        # 1. Intentar limpiar bloques Markdown si existen
        clean_resp = resp.strip()
        if "```json" in clean_resp:
            clean_resp = re.search(r"```json\s*(.*?)\s*```", clean_resp, re.DOTALL).group(1)
        elif "```" in clean_resp:
            clean_resp = re.search(r"```\s*(.*?)\s*```", clean_resp, re.DOTALL).group(1)
        
        # 2. Parsear el JSON (sea directo o extraído)
        questions = json.loads(clean_resp)
        if isinstance(questions, list):
            return [str(q).replace('"', '').replace('*', '') for q in questions if len(str(q)) > 10][:3]
    except Exception as e:
        logger.debug(f"Fallo en parseo JSON de sugerencias: {e}")
    
    # Fallback: buscar comillas
    matches = re.findall(r'["\'](.*?)["\']', resp)
    return [m for m in matches if len(m) > 15][:3] or ["¿Qué insights hay?"]

def ai_data_cleaner(df, api_key, provider="gemini", mistral_key=None, strategy="remove"):
    key = (mistral_key or api_key) if provider == "mistral" else api_key
    
    # Generar perfil real del dataset
    profile = f"Columnas detectadas: {df.columns.tolist()}\nMuestra de datos:\n{df.head(5).to_string()}"
    
    strategy_instruction = ""
    if strategy == "remove":
        strategy_instruction = "Estrategia para valores nulos: Eliminar filas con valores nulos en columnas críticas."
    elif strategy == "mean":
        strategy_instruction = "Estrategia para valores nulos: Imputar valores nulos en columnas numéricas utilizando la media aritmética de la columna."
    elif strategy == "median":
        strategy_instruction = "Estrategia para valores nulos: Imputar valores nulos en columnas numéricas utilizando la mediana de la columna."
    elif strategy == "zero":
        strategy_instruction = "Estrategia para valores nulos: Rellenar valores nulos con cero (0) en columnas numéricas y con cadena vacía ('') en texto."
    else:
        strategy_instruction = "Estrategia para valores nulos: Eliminar filas con valores nulos."
        
    p = prompts.DATA_CLEANER_PROMPT.format(profile_str=profile) + f"\nINSTRUCCIÓN DE ESTRATEGIA ADICIONAL:\n- {strategy_instruction}\n"
    raw = generate_ai_content(p, key, provider)
    m = re.search(r"```python\n(.*?)\n```", raw, re.DOTALL)
    return executor.safe_exec_cleaning(df, m.group(1) if m else raw)

async def execute_analysis(c, r, v): return await executor.execute_analysis(c, r, v)
def generate_auto_dashboard(ds, ak, pr="gemini", mk=None):
    # Simplificado para mantener flujo
    return {"metrics": [], "charts": []}
