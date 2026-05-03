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

# Configuración de Modelos
MODELS = {
    "GEMINI": "gemini-3.1-flash-lite-preview",
    "MISTRAL": "mistral-large-latest"
}

# Compatibilidad con mistralai
try:
    from mistralai import Mistral
except ImportError:
    Mistral = None
    logger.warning("Mistralai no instalado.")

def get_client(api_key):
    return genai.Client(api_key=api_key)

def validate_api_key(api_key, provider="gemini"):
    if not api_key: return False, "API Key vacía."
    try:
        if provider == "gemini":
            get_client(api_key).models.list()
        elif provider == "mistral":
            if Mistral: Mistral(api_key=api_key).models.list()
        return True, None
    except Exception as e:
        return False, f"Error en {provider}: {str(e)}"

def generate_ai_content(prompt, api_key, provider="gemini", temperature=0.7):
    """Generación con manejo amigable de errores de cuota."""
    if not api_key: return "Error: API Key no proporcionada."
    clean_key = api_key.strip()
    
    try:
        if provider == "gemini":
            client = get_client(clean_key)
            response = client.models.generate_content(
                model=MODELS["GEMINI"],
                contents=prompt,
                config=types.GenerateContentConfig(temperature=temperature)
            )
            return response.text
        elif provider == "mistral" and Mistral:
            client = Mistral(api_key=clean_key)
            resp = client.chat.complete(
                model=MODELS["MISTRAL"],
                messages=[{"role": "user", "content": prompt}]
            )
            return resp.choices[0].message.content
    except Exception as e:
        err = str(e).lower()
        if "429" in err or "quota" in err or "exhausted" in err:
            return f"⚠️ **¡Uy! Tu clave de {provider.capitalize()} se ha quedado sin créditos o llegó a su límite.**\nPor favor, actualiza tu API Key en la sección de Configuración para continuar."
        logger.error(f"Error AI ({provider}): {e}")
        return f"Error técnico: {str(e)}"

def analyze_data(data_context, query, api_key, chat_history=[], mode="file", provider="gemini", mistral_key=None, primary_source_name=None):
    """Analista Inteligente con soporte Dual (Híbrido) y Aislamiento de Contexto."""
    try:
        # Configuración de roles para modo DUAL (Híbrido)
        eng_provider = "gemini" if provider in ["gemini", "hybrid"] else "mistral"
        eng_key = api_key if eng_provider == "gemini" else (mistral_key or api_key)
        
        str_provider = "mistral" if provider in ["mistral", "hybrid"] else "gemini"
        str_key = (mistral_key or api_key) if str_provider == "mistral" else api_key

        # --- PASO 1: INGENIERÍA (CÓDIGO) ---
        if mode == "sql":
            prompt = prompts.SQL_ENGINEER_PROMPT.format(query=query, context_str=data_context["schema"])
            raw = generate_ai_content(prompt, eng_key, eng_provider)
            if "⚠️" in raw: return raw
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
        3. Visualización: Genera un gráfico relevante con la variable 'fig'.
        4. Responde siempre en Español con un tono profesional.

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
            if "⚠️" in raw: return raw
            
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
    p = prompts.BI_SUGGESTIONS_PROMPT.format(context_str="Analizando esquema...")
    resp = generate_ai_content(p, key, provider)
    matches = re.findall(r'["\'](.*?)["\']', resp)
    return [m for m in matches if len(m) > 15][:3] or ["¿Qué insights hay?"]

def ai_data_cleaner(df, api_key, provider="gemini", mistral_key=None):
    key = (mistral_key or api_key) if provider == "mistral" else api_key
    p = prompts.DATA_CLEANER_PROMPT.format(profile_str="Perfilando...")
    raw = generate_ai_content(p, key, provider)
    m = re.search(r"```python\n(.*?)\n```", raw, re.DOTALL)
    return executor.safe_exec_cleaning(df, m.group(1) if m else raw)

def execute_analysis(c, r, v): return executor.execute_analysis(c, r, v)
def generate_auto_dashboard(ds, ak, pr="gemini", mk=None):
    # Simplificado para mantener flujo
    return {"metrics": [], "charts": []}
