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
    Genera código Python/Pandas/SQL para el análisis basado en la consulta del usuario y el historial.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        if mode == "file":
            df = data_context
            context_str = f"""
            Dataset columns: {df.columns.tolist()}
            Shape: {df.shape}
            Head (3 rows): {df.head(3).to_string()}
            """
            data_var = "df"
        else:
            context_str = f"Database Schema:\n{data_context}"
            data_var = "engine"

        # Formatear el historial para el prompt
        history_str = ""
        for msg in chat_history[-5:]: # Enviamos los últimos 5 mensajes para contexto
            role = "Usuario" if msg["role"] == "user" else "Agente"
            history_str += f"{role}: {msg['content']}\n"

        prompt = f"""
        Eres un experto analista de BI y programador senior de Python.
        Contexto de datos ({mode}):
        {context_str}
        
        Historial de la conversación:
        {history_str}
        
        Pregunta actual: "{query}"
        
        Instrucciones de Programación y Visualización:
        1. Considera el historial para análisis evolutivos.
        2. Escribe un bloque de código Python encerrado en ```python ```.
        3. Usa la variable '{data_var}' como entrada.
        4. IMPORTANTE: Los nombres de columnas están limpios (strip).
        5. USA `print()` para explicar brevemente el hallazgo principal.
        
        Guía de Gráficos (Plotly):
        - SIEMPRE crea el objeto `fig` y usa el template `plotly_dark` para que combine con la UI.
        - Tendencias Temporales: `px.line` o `px.area`.
        - Comparaciones Categorical: `px.bar` (¡ordena los datos de mayor a menor!).
        - Partes de un todo: `px.pie` (con agujero central como 'donut') o `px.treemap` si hay muchas categorías.
        - Relaciones/Correlación: `px.scatter` con línea de tendencia si aplica.
        - Distribución: `px.histogram` o `px.box`.
        - Jerarquías: `px.sunburst` o `px.treemap`.
        - Personaliza: Añade títulos claros (`title`), etiquetas de ejes (`labels`) y una paleta de colores vibrante (ej: `color_discrete_sequence=px.colors.qualitative.Prism`).
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error en la comunicación con Gemini: {e}"

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
    Ejecuta el código generado y devuelve la salida textual y el objeto gráfico.
    """
    # Guardar el estado original
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    
    # Inyectar librerías
    local_vars = {var_name: context_obj, 'pd': pd, 'px': px}
    
    try:
        # Extraer código
        code_match = re.search(r"```python\n(.*?)```", raw_response, re.DOTALL)
        clean_code = code_match.group(1) if code_match else raw_response
        
        # Eliminar posibles llamadas a .show() o similares que bloqueen
        clean_code = clean_code.replace(".show()", "")
        
        exec(clean_code, {}, local_vars)
        
        output = redirected_output.getvalue()
        fig = local_vars.get('fig', None)
        
        sys.stdout = old_stdout
        return output, fig
    except Exception as e:
        sys.stdout = old_stdout
        return f"Error en ejecución: {e}\nCódigo generado:\n{raw_response}", None

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
