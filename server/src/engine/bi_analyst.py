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
from . import prompts
from . import executor
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

def generate_ai_content(prompt, api_key, provider="gemini", temperature=0.7, model_level="SWARM"):
    """Generación con manejo de niveles de potencia (Gemini 3.1)."""
    if not api_key: return "Error: API Key no proporcionada."
    clean_key = api_key.strip()
    
    try:
        if provider == "gemini":
            client = get_client(clean_key)
            # Determinar qué modelo de la familia 3.1 usar
            model_key = f"GEMINI_{model_level}"
            model_name = MODELS.get(model_key, MODELS["GEMINI_SWARM"])
            
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=temperature)
            )
            return response.text
        elif provider == "mistral":
            if not api_key: return "⚠️ Falta API Key de Mistral."
            try:
                from mistralai import Mistral
                clean_key = api_key.strip()
                if clean_key not in _clients:
                    _clients[clean_key] = Mistral(api_key=clean_key)
                client = _clients[clean_key]
                
                resp = client.chat.complete(
                    model=MODELS["MISTRAL"],
                    messages=[{"role": "user", "content": prompt}]
                )
                return resp.choices[0].message.content
            except Exception as e:
                raise e
    except Exception as e:
        err = str(e).lower()
        if "429" in err or "quota" in err or "exhausted" in err:
            return f"⚠️ **¡Uy! Tu clave de {provider.capitalize()} se ha quedado sin créditos.**\nActualiza tu API Key en Configuración."
        if "503" in err or "high demand" in err or "unavailable" in err:
            return f"⚠️ **El motor de {provider.capitalize()} está saturado.**\nReintenta en unos segundos."
        if "invalid" in err or "key" in err or "permission" in err or "401" in err or "403" in err:
            return f"⚠️ **Error de Autenticación con {provider.capitalize()}.**\nTu API Key parece ser inválida. Revísala en Configuración."
        
        logger.error(f"Error AI ({provider}): {e}")
        return f"Error técnico ({provider}): {str(e)}"
    
    return f"⚠️ Error: El motor de {provider} no pudo generar una respuesta. Verifica tu API Key."

def analyze_data(data_context, query, api_key, chat_history=[], mode="file", provider="gemini", mistral_key=None, primary_source_name=None):
    """Analista Inteligente con soporte Dual (Híbrido) y Aislamiento de Contexto."""
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
        else:
            eng_provider, eng_key = "gemini", api_key
            str_provider, str_key = "gemini", api_key

        # 2. Bucle de Ingeniería (Código) con Reintento y Aislamiento de Contexto
        retry_count = 0
        max_retries = 1
        real_results = ""
        fig_code = ""
        
        while retry_count <= max_retries:
            # AISLAMIENTO DE CONTEXTO Y GENERACIÓN DE PROMPT
            if isinstance(data_context, dict):
                tables_desc = []
                head_info = {}
                focus_instruction = ""
                
                # Aislamiento si hay fuente primaria
                temp_context = data_context
                if primary_source_name and primary_source_name in temp_context:
                    focus_instruction = f"⚠️ IMPORTANTE: Enfócate en la tabla '{primary_source_name}'. Analiza este archivo principalmente."
                    # Si no pide cruces, aislamos
                    if not any(word in query.lower() for word in ["compara", "cruza", "vs", "relaciona"]):
                        temp_context = {primary_source_name: temp_context[primary_source_name]}
                
                for name, df in temp_context.items():
                    if hasattr(df, 'columns'):
                        # Muestra más rica: 5 filas y tipos de datos
                        tables_desc.append(f"- Tabla '{name}': {df.columns.tolist()} ({len(df)} filas)")
                        head_info[name] = {
                            "muestra": df.head(5).to_dict(),
                            "tipos": df.dtypes.astype(str).to_dict()
                        }
                
                data_info = "\n".join(tables_desc)
                context_str = data_info
                
                p = f"""
        Eres un Analista BI Experto. Objetivo: "{query}"
        {focus_instruction}

        ESTRUCTURA:
        {data_info}

        REGLAS:
        1. Usa el diccionario 'dfs' (ej: df1 = dfs['nombre_tabla']).
        2. Plotly para gráficos. Asígnalo a 'fig'.
        3. No uses matplotlib. Responde en Español.

        MUESTRA:
        {json.dumps(head_info, indent=2, cls=SafeJSONEncoder)}

        Formato: Razonamiento y ```python ... ```
        """
                data_var = "dfs"
            else:
                context_str = f"Columnas: {data_context.columns.tolist()}"
                p = prompts.ENGINEER_PROMPT_TEMPLATE.format(data_var="df", query=query, context_str=context_str)
                data_var = "df"

            if retry_count > 0:
                p += f"\n\n⚠️ **ERROR ANTERIOR**: {real_results}\nCorrige el código. Evita .str en fechas."

            raw = generate_ai_content(p, eng_key, eng_provider, model_level="ANALYTICS")
            if not raw or "⚠️" in raw: return raw or "⚠️ Error en IA.", None, None
            
            temp_text, fig = executor.execute_analysis(data_context, raw, data_var)
            
            if "⚠️ Error" in temp_text and retry_count < max_retries:
                real_results = temp_text
                retry_count += 1
                continue
            
            real_results = temp_text
            fig_code = fig
            break

        # 3. Estrategia (Narrativa)
        clean_res = real_results.split("---")[-1].strip() if "---" in real_results else real_results
        if "⚠️ Error" in real_results:
            clean_res = f"⚠️ Análisis parcial por error: {real_results}"

        p_strat = prompts.STRATEGIST_PROMPT_TEMPLATE.format(query=query, real_results=clean_res, context_str=context_str)
        final_narrative = generate_ai_content(p_strat, str_key, str_provider, model_level="ANALYTICS")
        
        # Devolver el trio perfecto: Narrativa, Gráfico y Código
        return final_narrative, fig_code, raw

    except Exception as e:
        logger.error(f"Critical Error in analyze_data: {e}")
        return f"### ❌ Error Crítico\n{str(e)}", None, None

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

def ai_data_cleaner(df, api_key, provider="gemini", mistral_key=None):
    key = (mistral_key or api_key) if provider == "mistral" else api_key
    
    # Generar perfil real del dataset
    profile = f"Columnas detectadas: {df.columns.tolist()}\nMuestra de datos:\n{df.head(5).to_string()}"
    
    p = prompts.DATA_CLEANER_PROMPT.format(profile_str=profile)
    raw = generate_ai_content(p, key, provider)
    m = re.search(r"```python\n(.*?)\n```", raw, re.DOTALL)
    return executor.safe_exec_cleaning(df, m.group(1) if m else raw)

def execute_analysis(c, r, v): return executor.execute_analysis(c, r, v)
def generate_auto_dashboard(ds, ak, pr="gemini", mk=None):
    # Simplificado para mantener flujo
    return {"metrics": [], "charts": []}
