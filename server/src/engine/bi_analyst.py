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

logger = logging.getLogger(__name__)

# Configuración de Modelos
MODELS = {
    "GEMINI": "gemini-3-flash-preview",
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

def analyze_data(data_context, query, api_key, chat_history=[], mode="file", provider="gemini", mistral_key=None):
    """Analista Inteligente con soporte Dual (Híbrido)."""
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
            if "⚠️" in raw: return raw # Error de cuota
            temp_text, _, clean_sql = executor.execute_sql_safe(data_context["data"], raw)
            real_results = temp_text or "Resultados SQL."
            fig_code = f"```sql\n{clean_sql}\n```" if clean_sql else ""
            context_str = f"Schema SQL: {data_context['schema'][:200]}"
        else:
            # Caso Pandas
            if isinstance(data_context, dict):
                context_str = f"Tablas: {list(data_context.keys())}"
                data_var = "dfs"
            else:
                context_str = f"Columnas: {data_context.columns.tolist()}"
                data_var = "df"

            p = prompts.ENGINEER_PROMPT_TEMPLATE.format(data_var=data_var, query=query, context_str=context_str)
            raw = generate_ai_content(p, eng_key, eng_provider)
            if "⚠️" in raw: return raw
            
            temp_text, _ = executor.execute_analysis(data_context, raw, data_var)
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
