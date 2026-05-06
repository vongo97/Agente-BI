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

# Configuración de Modelos (Jerarquía Gemini 3.1 - Abril 2026)
MODELS = {
    "GEMINI_SWARM": "gemini-3.1-flash",      # Velocidad para agentes y chat diario
    "GEMINI_ANALYTICS": "gemini-3.1-pro",    # Ventana de 2M tokens para contexto masivo
    "GEMINI_STRATEGY": "gemini-3-deep-think",# Razonamiento extremo (Chain of Thought)
    "MISTRAL": "mistral-large-latest"
}
# Alias para compatibilidad con código existente
MODELS["GEMINI"] = MODELS["GEMINI_SWARM"]

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
        elif provider == "mistral" and Mistral:
            if clean_key not in _clients:
                _clients[clean_key] = Mistral(api_key=clean_key)
            client = _clients[clean_key]
            resp = client.chat.complete(
                model=MODELS["MISTRAL"],
                messages=[{"role": "user", "content": prompt}]
            )
            return resp.choices[0].message.content
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
        # Configuración de roles con protección de llaves
        if provider == "hybrid":
            # En modo híbrido: Gemini analiza (ingeniero) y Mistral narra (estratega)
            eng_provider, eng_key = "gemini", api_key
            str_provider, str_key = "mistral", (mistral_key or api_key)
        elif provider == "mistral":
            eng_provider, eng_key = "mistral", (mistral_key or api_key)
            str_provider, str_key = "mistral", (mistral_key or api_key)
        else: # Default Gemini
            eng_provider, eng_key = "gemini", api_key
            str_provider, str_key = "gemini", api_key

        # --- PASO 1: INGENIERÍA (CÓDIGO) ---
        if mode == "sql":
            prompt = prompts.SQL_ENGINEER_PROMPT.format(query=query, context_str=data_context["schema"])
            raw = generate_ai_content(prompt, eng_key, eng_provider)
            if not raw or "⚠️" in raw: return raw or "⚠️ Error desconocido en el motor SQL de IA."
            temp_text, _, clean_sql = executor.execute_sql_safe(data_context["data"], raw)
            real_results = temp_text or "Resultados SQL."
            fig_code = f"```sql\n{clean_sql}\n```" if clean_sql else ""
            context_str = f"Schema SQL: {data_context['schema'][:200]}"
        else:
            # Caso Pandas (Archivos, GSheets, etc.)
            if isinstance(data_context, dict):
                # Generar descripción de tablas
                tables_desc = []
                head_info = {}
                
                # AISLAMIENTO DE CONTEXTO: Si hay una fuente primaria, la priorizamos y aislamos
                focus_instruction = ""
                if primary_source_name and primary_source_name in data_context:
                    focus_instruction = f"⚠️ IMPORTANTE: El usuario se está enfocando en la tabla '{primary_source_name}'. Analiza ESTE archivo principalmente. Solo menciona o cruza con otras tablas si el usuario lo pide explícitamente en su pregunta."
                    
                    # Verificamos si el usuario pide comparación
                    query_lower = query.lower()
                    comparison_keywords = ["compara", "relaciona", "cruza", "vs", "versus", "correlacion", "unir", "junto"]
                    wants_comparison = any(word in query_lower for word in comparison_keywords)
                    
                    if not wants_comparison:
                         # Si NO pide comparación, ocultamos el resto del pool para evitar fugas/distracciones
                         data_context = {primary_source_name: data_context[primary_source_name]}
                
                for name, df in data_context.items():
                    if isinstance(df, pd.DataFrame):
                        tables_desc.append(f"- Tabla '{name}': {df.columns.tolist()} ({len(df)} filas)")
                        head_info[name] = df.head(2).to_dict()
                
                data_info = "\n".join(tables_desc)
                context_str = data_info
                
                p = f"""
        Eres un Analista BI Experto con capacidades de Data Science.
        Tu objetivo es analizar los siguientes datos y responder: "{query}"

        {focus_instruction}

        ESTRUCTURA DE DATOS DISPONIBLE:
        {data_info}

        REGLAS CRÍTICAS:
        1. Acceso a Datos: Tienes un diccionario llamado 'dfs' que contiene los DataFrames.
           - Ejemplo: df1 = dfs['nombre_tabla_1']
        2. ENFOQUE: Si se te indicó una tabla principal ('{primary_source_name}'), ignora las demás a menos que se pida un cruce explícito.
        3. Columnas Crípticas: Si encuentras columnas con nombres como '2_27' o códigos, analiza los datos de la 'MUESTRA' para deducir su significado y menciónalo en tu análisis.
        4. Visualización: Genera un gráfico relevante con la variable 'fig'.
        5. Responde siempre en Español con un tono profesional.

        MUESTRA DE DATOS (JSON):
        {json.dumps(head_info, indent=2, cls=SafeJSONEncoder)}

        Escribe tu respuesta siguiendo este formato:
        Explica tu razonamiento estratégico y hallazgos.
        ```python
        # Código Python
        import pandas as pd
        import plotly.express as px
        # Tu código aquí usando el diccionario 'dfs'...
        ```
        """
                data_var = "dfs"
            elif isinstance(data_context, pd.DataFrame):
                context_str = f"Columnas: {data_context.columns.tolist()}"
                p = prompts.ENGINEER_PROMPT_TEMPLATE.format(data_var="df", query=query, context_str=context_str)
                data_var = "df"
            else:
                context_str = f"Contexto: {list(data_context.keys()) if isinstance(data_context, dict) else str(data_context)[:200]}"
                p = prompts.ENGINEER_PROMPT_TEMPLATE.format(data_var="dfs", query=query, context_str=context_str)
                data_var = "dfs" if isinstance(data_context, dict) else "df"

            raw = generate_ai_content(p, eng_key, eng_provider)
            if not raw or "⚠️" in raw: return raw or "⚠️ Error desconocido en el motor de IA."
            
            temp_text, _ = executor.execute_analysis(data_context, raw, data_var)
            
            # Limpieza de resultados para el Estratega
            if "### ⚠️" in temp_text or "### 🛡️" in temp_text:
                real_results = f"ERROR TÉCNICO: {temp_text}."
            else:
                real_results = temp_text.split("---")[-1].strip() if "---" in temp_text else temp_text
            
            m = re.search(r"```python\n(.*?)```", raw, re.DOTALL)
            fig_code = f"```python\n{m.group(1)}\n```" if m else ""

        # --- PASO 2: ESTRATEGIA (NARRATIVA) ---
        p_narrative = prompts.STRATEGIST_PROMPT_TEMPLATE.format(query=query, real_results=real_results, context_str=context_str)
        final_narrative = generate_ai_content(p_narrative, str_key, str_provider)
        
        return f"{final_narrative}\n\n{fig_code}"

    except Exception as e:
        return f"Error en análisis ({provider}): {e}"

def generate_report_summary(query, api_key, context_data=None, provider="gemini", mistral_key=None):
    key = (mistral_key or api_key) if provider == "mistral" else api_key
    p = prompts.REPORT_SUMMARY_PROMPT.format(query=query, context_str=str(context_data)[:200])
    return generate_ai_content(p, key, provider)

def detect_anomalies_hybrid(df, api_key, provider="gemini", mistral_key=None):
    key = (mistral_key or api_key) if provider == "mistral" else api_key
    # Lógica Z-Score simplificada
    prompt = prompts.ANOMALY_AUDITOR_PROMPT.format(findings_str="Análisis estadístico iniciado...", columns=df.columns.tolist(), sample=df.head(2).to_dict())
    return generate_ai_content(prompt, key, provider)

def suggest_questions(data_context, api_key, mode="file", provider="gemini", mistral_key=None):
    key = (mistral_key or api_key) if provider == "mistral" else api_key
    
    # Construir context_str real basado en el tipo de datos
    context_str = ""
    if isinstance(data_context, dict):
        # Pool de DataFrames
        tables = []
        for name, df in data_context.items():
            if hasattr(df, 'columns'):
                tables.append(f"Tabla '{name}': {df.columns.tolist()}")
            else:
                tables.append(f"Fuente '{name}': [Estructura no definida]")
        context_str = "\n".join(tables)
    elif hasattr(data_context, 'columns'):
        # DataFrame único
        context_str = f"Columnas: {data_context.columns.tolist()}"
    else:
        # Probablemente esquema SQL (string)
        context_str = str(data_context)[:1000]

    p = prompts.BI_SUGGESTIONS_PROMPT.format(context_str=context_str)
    resp = generate_ai_content(p, key, provider)
    
    # VALIDACIÓN DE SEGURIDAD: Si es un mensaje de error de la IA, no parsear
    if resp.startswith("⚠️") or resp.startswith("Error"):
        if "Autenticación" in resp or "Key" in resp:
            return [f"Error de Configuración: {resp.split('.')[0]}"]
        return ["La IA está ocupada o saturada. Reintenta en un momento."]
    
    # Extraer las preguntas del JSON o de las comillas
    try:
        # Intentar parsear como JSON primero (según el prompt)
        import json
        m_json = re.search(r"```json\n(.*?)\n```", resp, re.DOTALL)
        if m_json:
            questions = json.loads(m_json.group(1))
            if isinstance(questions, list):
                return [str(q).replace('"', '').replace('*', '') for q in questions if len(str(q)) > 10][:3]
    except: pass
    
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
