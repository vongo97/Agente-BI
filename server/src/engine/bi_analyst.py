import google.generativeai as genai
import pandas as pd
import plotly.express as px
import sys
from io import StringIO
import re
import logging
logger = logging.getLogger(__name__)
import os

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
                context_str = "TABLAS DISPONIBLES:\n"
                for name, info in data_context.items():
                    context_str += f"- Tabla '{name}': Columnas {info['columns']}\n"
                    context_str += f"  Muestra: {info['sample']}\n\n"
                data_var = "dfs"
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
                tone_style='Estratégico, directo y sofisticado (Estilo Mistral/McKinsey)' if strategist_provider == 'mistral' else 'Analítico y claro',
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
                for name, info in data_context.items():
                    context_str += f"- {name}: {info['columns']}\n"
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
        
        # Intentar limpiar la respuesta por si la IA añade texto extra
        text = response_text.replace("```python", "").replace("```", "").strip()
        
        # Evaluar de forma segura (fallback si falla la evaluación)
        try:
            suggestions = eval(text)
            if isinstance(suggestions, list):
                return suggestions[:3]
        except:
            # Si falla el eval, intentar extraer con regex
            matches = re.findall(r'"([^"]*)"', text)
            if matches:
                return matches[:3]
                
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

import logging
logger = logging.getLogger(__name__)

def generate_auto_dashboard(df, api_key, provider="gemini", mistral_key=None):
    """
    Genera automáticamente 4 gráficos estratégicos basados en el DataFrame.
    Retorna una lista de diccionarios con {title, fig, insight}.
    """
    logger.info(f" Iniciando generate_auto_dashboard ({provider})...")
    
    effective_key = mistral_key if provider == "mistral" else api_key
    
    if not effective_key:
        logger.error(f"No API key provided for {provider}.")
        return []
        
    try:
        # 1. Analizar estructura
        buffer = StringIO()
        df.info(buf=buffer)
        info_str = buffer.getvalue()
        head_str = df.head(5).to_string()
        
        logger.info(f"Data context prepared. Rows: {len(df)}")

        # 2. Pedir ideas de gráficos (cantidad dinámica pero siempre al menos 2)
        planning_prompt = prompts.DASHBOARD_PLANNER_PROMPT.format(
            info_str=info_str,
            head_str=head_str
        )
        
        logger.info(f"Requesting dynamic plan from {provider}...")
        plan_response = generate_ai_content(planning_prompt, effective_key, provider)
        logger.info(f"Plan received (len={len(plan_response)})")
        
        # Limpieza básica del JSON
        plan_cleaned = plan_response.replace("```json", "").replace("```", "").strip()
        dashboard_plan = []
        import json
        try:
            dashboard_plan = json.loads(plan_cleaned)
            logger.info(f"✅ Plan parsed successfully: {len(dashboard_plan)} items")
            
            # Limitar a máximo 4 para evitar timeout
            if len(dashboard_plan) > 4:
                dashboard_plan = dashboard_plan[:4]
            # Si está vacío, usar fallback
            elif len(dashboard_plan) == 0:
                raise ValueError("Empty plan")
                
        except Exception as json_e:
            logger.error(f"JSON Parse Error: {json_e}. Content: {plan_cleaned[:200]}...")
            # Fallback garantizado: 2 gráficos básicos
            dashboard_plan = [
                {"title": "Resumen General", "query": "Crea un gráfico de barras mostrando las principales categorías o valores del dataset"},
                {"title": "Distribución Principal", "query": "Muestra un histograma o gráfico de la columna numérica más importante"}
            ]

        results = []
        
        # 3. Generar cada gráfico
        for idx, item in enumerate(dashboard_plan):
            query = item["query"]
            title = item["title"]
            logger.info(f"Generating Item {idx+1}: {title}...")
            
            code_prompt = prompts.DASHBOARD_GRAPH_CODE_PROMPT.format(
                query=query
            )
            
            try:
                code_resp = generate_ai_content(code_prompt, effective_key, provider)
                code_match = re.search(r"```python\n(.*?)```", code_resp, re.DOTALL)
                
                if code_match:
                    code_to_run = code_match.group(1).replace("fig.show()", "")
                    
                    # Ejecutar
                    old_stdout = sys.stdout
                    redirected_output = sys.stdout = StringIO()
                    namespace = {"df": df.copy(), "pd": pd, "px": px, "json": json}
                    
                    try:
                        exec(code_to_run, namespace)
                        fig_json_str = redirected_output.getvalue().strip()
                        
                        if not fig_json_str:
                             logger.warning(f"No output from exec for {title}")
                             results.append({"title": title, "error": "No se generó salida JSON."})
                             continue

                        # Intentar parsear el output como JSON
                        try:
                            fig_data = json.loads(fig_json_str)
                            
                            # Generar Insight breve
                            insight_prompt = f"Analiza este gráfico ({title}) y da un insight ultra breve de 1 frase."
                            insight = generate_ai_content(insight_prompt, effective_key, provider)
                            
                            results.append({
                                "title": title,
                                "fig": fig_data,
                                "insight": insight
                            })
                            logger.info(f"Item {title} generated successfully.")
                        except json.JSONDecodeError as je:
                            logger.error(f"JSON Output Error for {title}: {je}. output: {fig_json_str[:50]}...")
                            results.append({
                                "title": title, 
                                "error": "Error formato gráfico."
                            })
                            
                    except Exception as exec_e:
                        logger.error(f"Exec Error {title}: {exec_e}")
                        results.append({"title": title, "error": str(exec_e)})
                    finally:
                        sys.stdout = old_stdout
                else:
                    logger.warning(f"No python code found for {title}")
            except Exception as item_e:
                logger.error(f"Generation Error {title}: {item_e}")
            
        logger.info(f"Finished. Returning {len(results)} items.")
        return results
    except Exception as e:
        logger.error(f"Critical Error in generate_auto_dashboard: {e}", exc_info=True)
        return []

