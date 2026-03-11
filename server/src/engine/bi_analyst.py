import google.generativeai as genai
import pandas as pd
import plotly.express as px
import sys
from io import StringIO
import re
import logging
logger = logging.getLogger(__name__)
import os
import json

# Nuevos módulos refactorizados
from . import prompts
from . import executor

# Compatibilidad con mistralai >= 1.0.0
try:
    from mistralai import Mistral
except ImportError:
    try:
        from mistralai.client import MistralClient as Mistral 
    except ImportError:
        Mistral = None
        logger.warning("Mistralai no está instalado. El proveedor 'mistral' y 'hybrid' no funcionarán.")

def validate_api_key(api_key, provider="gemini"):
    """
    Verifica si la API Key es válida.
    """
    if not api_key:
        return False, "La API Key está vacía."
    
    if provider == "gemini":
        try:
            genai.configure(api_key=api_key)
            genai.list_models()
            return True, None
        except Exception as e:
            return False, f"Error Gemini: {str(e)}"
    elif provider == "mistral":
        try:
            client = Mistral(api_key=api_key)
            client.models.list()
            return True, None
        except Exception as e:
            return False, f"Error Mistral: {str(e)}"
    
    return True, None

# --- HELPERS PARA MULTI-ENGINE ---

def get_gemini_response(prompt, api_key, model_name="gemini-2.5-flash"):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        return f"Error Gemini: {e}"

def get_mistral_response(prompt, api_key, model_name="mistral-large-latest"):
    try:
        clean_key = api_key.strip()
        logger.info(f"Initializing Mistral Client with key ending in ...{clean_key[-4:] if len(clean_key)>4 else 'short'}")
        
        client = Mistral(api_key=clean_key)
        
        # Ajuste para v1.0.0+: client.chat.complete
        chat_response = client.chat.complete(
            model=model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        return chat_response.choices[0].message.content
    except Exception as e:
        logger.error(f"Mistral Error: {e}")
        return f"Error Mistral: {e}"

def generate_ai_content(prompt, api_key, provider="gemini", mistral_key=None):
    if provider == "mistral":
        # Si el provider es mistral, usamos la key específica si existe, o la genérica
        key = mistral_key if mistral_key else api_key
        if not key:
             return "Error: No Mistral Key provided"
        return get_mistral_response(prompt, key)
    elif provider == "gemini":
        return get_gemini_response(prompt, api_key)
    elif provider == "hybrid":
        # En hybrid, para generación simple de contenido, usamos Gemini por velocidad
        return get_gemini_response(prompt, api_key)
    return "Proveedor no válido"

def analyze_data(data_context, query, api_key, chat_history=[], mode="file", provider="gemini", mistral_key=None):
    """
    Genera un análisis.
    - provider="gemini": Todo con Gemini.
    - provider="mistral": Todo con Mistral.
    - provider="hybrid": Gemini genera Código (Ingeniero) -> Mistral genera Narrativa (Estratega).
    """
    
    # Configuración de Keys
    gemini_key = api_key
    mistral_k = mistral_key if mistral_key else api_key # Fallback si el usuario puso la de mistral en el campo principal (no recomendado pero posible)
    
    # 1. SELECCIÓN DEL INGENIERO (Generador de Código)
    # En modo híbrido o gemini, el ingeniero es Gemini.
    engineer_provider = "gemini" if provider in ["gemini", "hybrid"] else "mistral"
    engineer_key = gemini_key if engineer_provider == "gemini" else mistral_k

    # 2. SELECCIÓN DEL ESTRATEGA (Narrador)
    # En modo híbrido o mistral, el estratega es Mistral.
    strategist_provider = "mistral" if provider in ["mistral", "hybrid"] else "gemini"
    strategist_key = mistral_k if strategist_provider == "mistral" else gemini_key

    if provider == "hybrid" and (not gemini_key or not mistral_k):
        return "Error: Para el modo 'Segundo Cerebro' (Híbrido) necesitas ambas API Keys configuradas."

    try:
        # --- PASO 1: GENERACIÓN DE CÓDIGO Y DATOS REALES (EL INGENIERO) ---
        if mode == "file":
            # Caso Multinivel / Multitabla
            if isinstance(data_context, dict):
                context_str = "ESTRUCTURA DE DATOS (Objeto `dfs`):\n"
                table_names = list(data_context.keys())
                for name, obj in data_context.items():
                    if isinstance(obj, pd.DataFrame):
                        cols = obj.columns.tolist()
                        sample = obj.head(3).to_dict()
                    else:
                        cols = obj.get('columns', [])
                        sample = obj.get('sample', {})
                    
                    context_str += f"- Tabla: '{name}' (Puedes usar `dfs['{name}']` o simplemente `df` o `ventas`)\n"
                    context_str += f"  Columnas: {cols}\n"
                    context_str += f"  Muestra: {sample}\n\n"
                
                data_var = "dfs"
                
                # REGLA DE ORO DE FIABILIDAD:
                if len(table_names) == 1:
                     context_str += f"\n¡CRÍTICO!: Solo hay un archivo cargado. Usa directamente el nombre `df` o `ventas` para acceder a él.\n"
            else:
                # Caso tradicional (Single DataFrame)
                df = data_context
                context_str = f"Columns: {df.columns.tolist()}\nTotal Rows: {df.shape[0]}\nSample Data (First 5 rows):\n{df.head(5).to_string()}"
                data_var = "df"
        else:
            context_str = f"Schema: {data_context}"
            data_var = "engine"

        code_prompt = prompts.ENGINEER_PROMPT_TEMPLATE.format(
            data_var=data_var,
            query=query,
            context_str=context_str
        )
        
        # El Ingeniero genera el código
        code_response = generate_ai_content(code_prompt, engineer_key, engineer_provider)
        code_match = re.search(r"```python\n(.*?)```", code_response, re.DOTALL)
        
        real_results = "No se pudieron obtener resultados numéricos."
        fig_code = ""
        
        if code_match:
            code_to_run = code_match.group(1).replace(".show()", "")
            fig_code = f"```python\n{code_to_run}\n```"
            
            # Ejecución interna para capturar números usando el nuevo executor
            # Nota: analyze_data captura resultados para el Estratega
            temp_text, _ = executor.execute_analysis(data_context, code_response, data_var)
            # Extraer solo la parte de "Detalles técnicos" (stdout) si existe
            if "---" in temp_text:
                real_results = temp_text.split("---")[-1].strip()
            else:
                real_results = temp_text or "Cálculo ejecutado."

        # --- PASO 2: GENERACIÓN DE NARRATIVA ESTRATÉGICA (EL ESTRATEGA) ---
        history_str = ""
        for msg in chat_history[-3:]:
            role = "Usuario" if msg["role"] == "user" else "Agente"
            history_str += f"{role}: {msg['content']}\n"

        # SELECCIÓN DE PROMPT (Análisis vs Presentación)
        is_presentation = any(word in query.lower() for word in ["presentación", "presentacion", "diapositiva", "slides", "deck"])
        
        if is_presentation:
            narrative_prompt = prompts.PRESENTATION_PROMPT.format(
                query=query,
                real_results=real_results
            )
        else:
            narrative_prompt = prompts.STRATEGIST_PROMPT_TEMPLATE.format(
                query=query,
                real_results=real_results,
                context_str=context_str
            )
        
        # El Estratega genera la narrativa
        final_narrative = generate_ai_content(narrative_prompt, strategist_key, strategist_provider)
        
        # Combinamos para que el motor principal (execute_analysis) pueda procesarlo
        return f"{final_narrative}\n\n{fig_code}"

    except Exception as e:
        return f"Error en el 'Segundo Cerebro' ({provider}): {e}"

# Mantener compatibilidad con llamadas antiguas si es necesario, redireccionando a la nueva
def analyze_with_gemini(data_context, query, api_key, chat_history=[], mode="file", model_name="gemini-2.5-flash"):
    return analyze_data(data_context, query, api_key, chat_history, mode, provider="gemini")

def generate_report_narrative(data_context, query, api_key, mode="file", model_name="gemini-2.5-flash"):
    """
    Genera una narrativa profesional y profunda sobre los resultados de un análisis.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        if mode == "file":
            df = data_context
            context_str = f"Dataset: {df.columns.tolist()}. Head: {df.head(5).to_string()}"
        else:
            context_str = f"Schema: {data_context}"

        prompt = prompts.EXECUTIVE_REPORT_PROMPT.format(
            query=query,
            context_str=context_str
        )
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error en narrativa: {e}"

def execute_analysis(context_obj, raw_response, var_name):
    """
    Proxy para el nuevo módulo executor.
    """
    return executor.execute_analysis(context_obj, raw_response, var_name)

def detect_anomalies_hybrid(df: pd.DataFrame, api_key: str):
    """
    Sistema Híbrido: Detecta anomalías matemáticas con Pandas (Z-score) 
    y las interpreta estratégicamente con Gemini.
    """
    try:
        numeric_cols = df.select_dtypes(include=['number']).columns
        findings = []
        
        # 1. Detección de Outliers (Z-Score)
        for col in numeric_cols:
            mean = df[col].mean()
            std = df[col].std()
            if std == 0: continue
            
            # Buscamos valores con Z-Score > 3 (Extremos)
            outliers = df[abs((df[col] - mean) / std) > 3]
            
            if not outliers.empty:
                count = len(outliers)
                val_max = outliers[col].max()
                findings.append(f"- Se detectaron {count} valores atípicos en la columna '{col}'. El valor máximo detectado es {val_max} (Promedio: {mean:.2f}).")

        if not findings:
            findings_str = "No se detectaron desviaciones estadísticas significativas (Z-Score > 3) en los datos numéricos."
        else:
            findings_str = "\n".join(findings)

        # 2. Interpretación con Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = prompts.ANOMALY_AUDITOR_PROMPT.format(
            findings_str=findings_str,
            columns=df.columns.tolist(),
            sample=df.head(5).to_dict()
        )
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Error en el detector de anomalías: {e}"

def suggest_questions(data_context, api_key, mode="file", provider="gemini", mistral_key=None):
    """
    Analiza el esquema de los datos y sugiere 3 preguntas de análisis de alto valor.
    """
    effective_key = mistral_key if provider == "mistral" else api_key
    
    if not effective_key:
        return ["Configura tu API Key para ver sugerencias"]
    
    try:
        if mode == "file":
            # Soporte multitabla
            if isinstance(data_context, dict):
                context_str = "TABLAS DISPONIBLES:\n"
                for name, df_obj in data_context.items():
                    # Manejar si es un DF real o un dict descriptivo
                    if isinstance(df_obj, pd.DataFrame):
                        cols = df_obj.columns.tolist()
                    else:
                        cols = df_obj.get('columns', [])
                    context_str += f"- {name}: {cols}\n"
            else:
                df = data_context
                context_str = f"Dataset: {df.columns.tolist()}. Tipos: {df.dtypes.to_dict()}"
        else:
            context_str = f"Schema: {data_context}"

        prompt = prompts.BI_SUGGESTIONS_PROMPT.format(
            context_str=context_str
        )
        
        # Usar el provider seleccionado
        response_text = generate_ai_content(prompt, effective_key, provider, mistral_key)
        
        # Limpieza robusta
        # 1. Intentar encontrar un bloque JSON explícito
        json_match = re.search(r'```json\n?(.*?)\n?```', response_text, re.DOTALL)
        text_to_parse = json_match.group(1) if json_match else response_text
        
        # 2. Limpiar caracteres basura
        text_to_parse = text_to_parse.strip()
        
        # 3. Intentar parsear como lista
        try:
            import json
            suggestions = json.loads(text_to_parse)
            if isinstance(suggestions, list):
                # Filtrar fragmentos cortos (ej. "y") y asegurar que sean strings
                valid_s = [str(s).strip() for s in suggestions if len(str(s).strip()) > 15]
                if valid_s:
                    return valid_s[:3]
        except:
            pass
            
        try:
            # Fallback: Extraer todo lo que esté entre comillas o balanceado
            matches = re.findall(r'["\'](.*?)["\']', text_to_parse)
            valid_matches = [m.strip() for m in matches if len(m.strip()) > 15]
            if len(valid_matches) >= 1:
                return valid_matches[:3]
        except:
            pass

        return ["¿Cuál es el resumen general de mis datos?", "¿Cuáles son las métricas clave?", "¿Hay alguna anomalía importante?"]
        
    except Exception as e:
        print(f"[DEBUG] Error en suggest_questions: {e}")
        return ["Error al generar sugerencias"]

def ai_data_cleaner(df: pd.DataFrame, api_key: str, model_name: str = "gemini-2.5-flash"):
    """
    Analiza y limpia el DataFrame usando IA.
    """
    if not api_key:
        return df, "Error: No se proporcionó API Key"

    try:
        # 1. Perfilado básico del dataset
        nulls = df.isnull().sum().to_dict()
        duplicates = int(df.duplicated().sum())
        cols = df.columns.tolist()
        # Convertir dtypes a string para que sea serializable en el prompt
        dtypes = {k: str(v) for k, v in df.dtypes.to_dict().items()}
        sample = df.head(3).to_dict()

        profile_str = f"Columnas: {cols}\nTipos: {dtypes}\nNulos: {nulls}\nDuplicados: {duplicates}\nMuestra: {sample}"

        # 2. Consultar a Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        prompt = prompts.DATA_CLEANER_PROMPT.format(
            profile_str=profile_str
        )

        response = model.generate_content(prompt)
        code_match = re.search(r"```python\n(.*?)\n```", response.text, re.DOTALL)
        if not code_match:
            # Fallback a búsqueda de texto si no hay bloques
            code = response.text
        else:
            code = code_match.group(1)

        # 3. Ejecución segura usando el nuevo executor
        cleaned_df, summary = executor.safe_exec_cleaning(df, code)
        return cleaned_df, summary

    except Exception as e:
        import traceback
        print(f"[DEBUG] Error en ai_data_cleaner: {e}")
        print(traceback.format_exc())
        return df, f"Vaya, algo salió mal en la limpieza: {str(e)}"

def calculate_global_metrics(df, api_key, provider="gemini", mistral_key=None):
    """
    Usa IA para identificar y calcular KPIs clave del dataset.
    """
    effective_key = mistral_key if provider == "mistral" else api_key
    if not effective_key:
        return []
        
    try:
        buffer = StringIO()
        df.info(buf=buffer)
        info_str = buffer.getvalue()
        head_str = df.head(5).to_string()
        
        prompt = prompts.GLOBAL_METRICS_PROMPT.format(
            info_str=info_str,
            head_str=head_str
        )
        
        response = generate_ai_content(prompt, effective_key, provider)
        # Limpieza de JSON
        json_str = response.replace("```json", "").replace("```", "").strip()
        data = json.loads(json_str)
        return data.get("metrics", [])
    except Exception as e:
        logger.error(f"Error calculando métricas: {e}")
        return []

def generate_auto_dashboard(df, api_key, provider="gemini", mistral_key=None):
    """
    Genera automáticamente métricas y 4 gráficos estratégicos basados en el DataFrame.
    """
    logger.info(f" Iniciando generate_auto_dashboard ({provider})...")
    
    # 1. Calcular métricas globales primero
    metrics = calculate_global_metrics(df, api_key, provider, mistral_key)
    
    effective_key = mistral_key if provider == "mistral" else api_key
    if not effective_key:
        return {"metrics": metrics, "charts": []}
        
    try:
        # Analizar estructura para planificación de gráficos
        buffer = StringIO()
        df.info(buf=buffer)
        info_str = buffer.getvalue()
        head_str = df.head(5).to_string()

        # 2. Pedir ideas de gráficos
        planning_prompt = prompts.DASHBOARD_PLANNER_PROMPT.format(
            info_str=info_str,
            head_str=head_str
        )
        
        plan_response = generate_ai_content(planning_prompt, effective_key, provider)
        plan_cleaned = plan_response.replace("```json", "").replace("```", "").strip()
        
        dashboard_plan = []
        try:
            dashboard_plan = json.loads(plan_cleaned)
            if len(dashboard_plan) > 4: dashboard_plan = dashboard_plan[:4]
        except:
            dashboard_plan = [
                {"title": "Distribución General", "query": "Crea un gráfico de barras del dataset"},
                {"title": "Métricas Clave", "query": "Muestra un histograma de los valores principales"}
            ]

        charts = []
        # 3. Generar cada gráfico
        for item in dashboard_plan:
            query = item["query"]
            title = item["title"]
            
            code_prompt = prompts.DASHBOARD_GRAPH_CODE_PROMPT.format(query=query)
            try:
                code_resp = generate_ai_content(code_prompt, effective_key, provider)
                code_match = re.search(r"```python\n(.*?)```", code_resp, re.DOTALL)
                
                if code_match:
                    code_to_run = code_match.group(1).replace("fig.show()", "")
                    old_stdout, sys.stdout = sys.stdout, StringIO()
                    namespace = {"df": df.copy(), "pd": pd, "px": px, "json": json}
                    
                    try:
                        exec(code_to_run, namespace)
                        fig_json_str = sys.stdout.getvalue().strip()
                        if fig_json_str:
                            fig_data = json.loads(fig_json_str)
                            insight_prompt = f"Basado en este gráfico ({title}), dame una conclusión de 1 frase."
                            insight = generate_ai_content(insight_prompt, effective_key, provider)
                            charts.append({"title": title, "fig": fig_data, "insight": insight})
                    finally:
                        sys.stdout = old_stdout
            except Exception as e:
                logger.error(f"Error generando gráfico {title}: {e}")

        return {
            "metrics": metrics,
            "charts": charts
        }
    except Exception as e:
        logger.error(f"Critical Error in generate_auto_dashboard: {e}")
        return {"metrics": metrics, "charts": []}
