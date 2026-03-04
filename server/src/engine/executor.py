import sys
import pandas as pd
import plotly.express as px
import numpy as np
import json
import re
from io import StringIO
import logging

logger = logging.getLogger(__name__)

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

    clean_code = code_match.group(1).replace(".show()", "")

    # --- SEGURIDAD: Sandboxing ---
    # Bloquear palabras clave peligrosas antes de la ejecución
    
    # 1. Limpiar el código por si la IA añade comentarios descriptivos con palabras prohibidas
    code_to_check = re.sub(r'#.*', '', clean_code)
    
    # RELAJADO TEMPORALMENTE A PETICIÓN DEL USUARIO PARA EVITAR FALSOS POSITIVOS PERSISTENTES
    # forbidden = ["import ", "os.", "sys.", "subprocess", "shutil", "open(", "eval(", "exec(", "getattr", "setattr", "delattr", "socket", "requests"]
    # for word in forbidden:
    #     if word in code_to_check:
    #         logger.warning(f"BLOCKED CODE ATTEMPT: '{word}' found in generated code.")
    #         # Loguear el código completo para auditoría
    #         with open("security_blocks.log", "a", encoding="utf-8") as f:
    #             f.write(f"\n--- BLOCKED {word} ---\n{clean_code}\n-------------------\n")
    #             
    #         return f"### 🛡️ Bloqueo de Seguridad\nSe detectó una operación no permitida (`{word}`) en el código generado. El análisis ha sido abortado por seguridad.", None

    # 2. Ejecutar código para obtener el gráfico
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    
    # Definir builtins restringidos (SIN __import__)
    safe_builtins = {
        'print': print,
        'range': range,
        'len': len,
        'str': str,
        'int': int,
        'float': float,
        'list': list,
        'dict': dict,
        'round': round,
        'sum': sum,
        'min': min,
        'max': max,
        'abs': abs,
        'enumerate': enumerate,
        'any': any,
        'all': all,
        'zip': zip,
        'bool': bool,
        'sorted': sorted,
        'reversed': reversed,
        'Exception': Exception,
        'ValueError': ValueError,
        'TypeError': TypeError,
        'StopIteration': StopIteration
    }

    exec_globals = {
        var_name: context_obj, 
        'pd': pd, 
        'px': px, 
        'np': np, 
        'json': json,
        '__builtins__': safe_builtins
    }
    
    try:
        exec(clean_code, exec_globals, exec_globals)
        
        code_stdout = redirected_output.getvalue().strip()
        fig = exec_globals.get('fig', None)
        
        final_text = narrative
        if code_stdout:
            if not any(x in code_stdout.lower() for x in ["<class", "dtype:", "memory usage"]):
                final_text += f"\n\n---\n{code_stdout}"
        
        return final_text, fig
    except KeyError as e:
        available_keys = list(context_obj.keys()) if isinstance(context_obj, dict) else "N/A"
        logger.error(f"KeyError: {e}. Available keys: {available_keys}")
        return f"### ⚠️ Error de Referencia\nLa IA intentó acceder a una tabla o columna llamada `{e}`, pero no existe.\n\n**Tablas disponibles:** `{available_keys}`", None
    except TypeError as e:
        if "unhashable type: 'list'" in str(e) and isinstance(context_obj, dict):
            return f"### ⚠️ Error de Estructura\nLa IA intentó acceder a múltiples tablas a la vez de forma incorrecta (ej: `dfs[['tabla1', 'tabla2']]`).\n\n**Solución**: Debe acceder a una sola tabla a la vez usando `dfs['nombre_tabla']`.", None
        logger.error(f"TypeError: {e}")
        return f"### ⚠️ Error de Tipo\nHubo un problema de compatibilidad en el código: {e}", None
    except Exception as e:
        logger.error(f"Execution Error: {e}")
        return f"### ⚠️ Error en el Procesamiento\nHubo un problema ejecutando el análisis lógico solicitado.\n\n*Detalle técnico: {e}*", None
    finally:
        sys.stdout = old_stdout

def safe_exec_cleaning(df, code):
    """
    Ejecutor especializado para tareas de limpieza de datos con sandbox.
    """
    # 1. Limpiar el código por si la IA añade comentarios descriptivos
    code_to_check = re.sub(r'#.*', '', code)
    
    # Verificación de seguridad rápida (RELAJADA TEMPORALMENTE)
    # forbidden = ["import ", "os.", "sys.", "subprocess", "open(", "eval(", "exec("]
    # for word in forbidden:
    #     if word in code_to_check:
    #          logger.warning(f"BLOCKED CLEANING CODE ATTEMPT: '{word}'")
    #          return df, f"Error: Código de limpieza bloqueado por seguridad (palabra '{word}' prohibida)."

    initial_rows = len(df)
    
    # Namespace restringido para limpieza
    safe_builtins = {
        'len': len, 'str': str, 'int': int, 'float': float,
        'list': list, 'dict': dict, 'range': range
    }
    
    namespace = {
        "df": df.copy(), 
        "pd": pd, 
        "np": np,
        "__builtins__": safe_builtins
    }
    
    try:
        exec(code, namespace, namespace)
        cleaned_df = namespace.get("df")
        summary = namespace.get("clean_summary", "Limpieza completada.")
        
        if len(cleaned_df) < initial_rows and len(cleaned_df) <= 5 and initial_rows > 10:
             return df, "Error: La IA intentó truncar los datos erróneamente. Revertido por seguridad."
             
        return cleaned_df, summary
    except Exception as e:
        logger.error(f"Cleaning Execution Error: {e}")
        raise e
