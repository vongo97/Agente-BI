import google.generativeai as genai
import pandas as pd
import plotly.express as px
import sys
from io import StringIO
import re

def validate_api_key(api_key):
    """
    Verifica si la API Key es válida intentando listar los modelos disponibles.
    Devuelve (True, None) si es válida, o (False, error_message) si falla.
    """
    if not api_key:
        return False, "La API Key está vacía."
    
    try:
        genai.configure(api_key=api_key)
        # Intentamos una operación ligera para validar la clave
        genai.list_models()
        return True, None
    except Exception as e:
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg:
            return False, "La API Key no es válida (API_KEY_INVALID)."
        elif "PermissionDenied" in error_msg:
            return False, "Permiso denegado. Verifica que la API Key tenga habilitado el servicio de Generative Language."
        return False, f"Error de conexión: {error_msg}"

def analyze_with_gemini(data_context, query, api_key, chat_history=[], mode="file", model_name="gemini-2.5-flash"):
    """
    Genera un análisis de dos pasos: 
    1. Genera y ejecuta código para obtener datos reales.
    2. Genera la narrativa estratégica basada en esos datos reales.
    """
    if not api_key:
        return "Error: API Key no proporcionada."
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        # --- PASO 1: GENERACIÓN DE CÓDIGO Y DATOS REALES ---
        if mode == "file":
            df = data_context
            context_str = f"Columns: {df.columns.tolist()}. Shape: {df.shape}. Head: {df.head(2).to_dict()}"
            data_var = "df"
        else:
            context_str = f"Schema: {data_context}"
            data_var = "engine"

        code_prompt = f"""
        Genera código Python para analizar estos datos y responder: "{query}".
        
        REGLAS TÉCNICAS:
        1. Usa la variable `{data_var}` que ya está cargada.
        2. LIMPZA: Si una columna numérica tiene símbolos ($, €, %) o es string, límpiala con `pd.to_numeric(..., errors='coerce')`.
        3. RESULTADOS: Usa `print()` para mostrar CADA cifra importante que encuentres. Ejemplo: `print(f'Ticket Promedio: {{avg}}')`.
        4. GRÁFICO: Genera SIEMPRE un objeto `fig` con Plotly Express usando `template='plotly_dark'`.
        
        Contexto del esquema:
        {context_str}
        
        Genera solo el bloque de código entre triple comilla invertida.
        """
        
        code_response = model.generate_content(code_prompt).text
        code_match = re.search(r"```python\n(.*?)```", code_response, re.DOTALL)
        
        real_results = "No se pudieron obtener resultados numéricos."
        fig_code = ""
        
        if code_match:
            code_to_run = code_match.group(1).replace(".show()", "")
            fig_code = f"```python\n{code_to_run}\n```"
            
            # Ejecución interna para capturar números
            old_stdout = sys.stdout
            redirected_output = sys.stdout = StringIO()
            local_vars = {data_var: data_context, 'pd': pd, 'px': px}
            try:
                exec(code_to_run, {}, local_vars)
                real_results = redirected_output.getvalue().strip() or "Cálculo ejecutado con éxito."
            except Exception as e:
                real_results = f"Error en ejecución: {e}"
            finally:
                sys.stdout = old_stdout

        # --- PASO 2: GENERACIÓN DE NARRATIVA ESTRATÉGICA ---
        history_str = ""
        for msg in chat_history[-3:]:
            role = "Usuario" if msg["role"] == "user" else "Agente"
            history_str += f"{role}: {msg['content']}\n"

        narrative_prompt = f"""
        Eres un Socio de Consultoría Estratégica Senior. Escribe un informe sobre: "{query}".
        
        DATOS REALES VERIFICADOS (Usa estos números OBLIGATORIAMENTE):
        {real_results}
        
        INSTRUCCIONES:
        1. NO inventes cifras. Usa solo los DATOS REALES arriba indicados.
        2. Estructura: ## Título, ### Análisis, ### Recomendaciones.
        3. Formato: Doble salto de línea, negritas en cifras y listas con viñetas.
        4. Sé profundo y estratégico: explica el "porqué" de esos números para el negocio.
        
        Muestra del esquema para contexto adicional:
        {context_str}
        """
        
        final_narrative = model.generate_content(narrative_prompt).text
        
        # Combinamos para que el motor principal (execute_analysis) pueda procesarlo
        return f"{final_narrative}\n\n{fig_code}"

    except Exception as e:
        return f"Error en el motor de pensamiento dual: {e}"

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

        prompt = f"""
        Como un Consultor Estratégico Senior, genera un Informe Ejecutivo basado en esta consulta: "{query}".
        
        Contexto de datos:
        {context_str}
        
        El informe debe ser profesional, formal y estructurado. Debe incluir:
        1. **Resumen Ejecutivo**: Un párrafo de alto nivel.
        2. **Análisis del 'Por Qué'**: Explica posibles causas o lógica de negocio detrás de los números (usa fórmulas si es necesario).
        3. **Implicaciones**: Qué significan estos resultados para el futuro del negocio.
        4. **Recomendaciones Estratégicas**: 3 acciones concretas.
        
        IMPORTANTE: No uses código Python aquí. Solo texto narrativo de alta calidad empresarial. 
        Usa un tono persuasivo y experto.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error en narrativa: {e}"

def execute_analysis(context_obj, raw_response, var_name):
    """
    Ejecuta el código generado y devuelve la narrativa del asistente + el objeto gráfico.
    Separamos el texto de la respuesta (IA) del código a ejecutar.
    """
    # 1. Separar narrativa de código
    narrative = re.sub(r"```python\n(.*?)```", "", raw_response, flags=re.DOTALL).strip()
    code_match = re.search(r"```python\n(.*?)```", raw_response, re.DOTALL)
    
    if not code_match:
        return narrative, None

    # 2. Ejecutar código para obtener el gráfico
    clean_code = code_match.group(1).replace(".show()", "")
    
    # Capturar salida del código (por si la IA insiste en print, pero priorizamos la narrativa)
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    
    local_vars = {var_name: context_obj, 'pd': pd, 'px': px}
    
    try:
        exec(clean_code, {}, local_vars)
        code_stdout = redirected_output.getvalue().strip()
        fig = local_vars.get('fig', None)
        
        # Si el código generó texto (print), lo añadimos al final de la narrativa como "Detalles técnicos"
        # pero de forma sutil
        final_text = narrative
        if code_stdout:
            # Si el stdout contiene basura técnica, lo ignoramos mejor
            if not any(x in code_stdout.lower() for x in ["<class", "dtype:", "memory usage"]):
                final_text += f"\n\n---\n{code_stdout}"
        
        sys.stdout = old_stdout
        return final_text, fig
    except Exception as e:
        sys.stdout = old_stdout
        return f"### ⚠️ Error en el Procesamiento\nHubo un problema ejecutando el análisis lógico solicitado.\n\n*Detalle técnico: {e}*", None

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
        
        prompt = f"""
        Actúa como un Auditor de Datos Senior. He realizado un análisis estadístico sobre un dataset y estos son los hallazgos:
        
        {findings_str}
        
        Información del Dataset:
        Columnas: {df.columns.tolist()}
        Muestra de Datos: {df.head(5).to_dict()}
        
        Tu tarea:
        1. Evalúa la criticidad de estos hallazgos (Baja, Media, Alta).
        2. Explica racionalmente por qué estos "outliers" podrían ser importantes para el negocio.
        3. Si no hay anomalías, felicita al usuario por la consistencia de sus datos y menciona una tendencia positiva que veas en la muestra.
        
        Formato: Usa Markdown con emojis. Sé directo y profesional.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Error en el detector de anomalías: {e}"
