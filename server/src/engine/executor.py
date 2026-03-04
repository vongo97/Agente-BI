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
    # Limpiamos el código para auditoría básica
    code_to_check = re.sub(r'#.*', '', clean_code)
    
    # 2. Ejecutar código para obtener el gráfico
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    
    # --- IMPORTACIÓN RESTRINGIDA: Para evitar errores 'import not found' ---
    def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
        # Mapeamos nombres comunes a los objetos ya cargados
        safe_modules = {
            'pandas': pd,
            'numpy': np,
            'plotly.express': px,
            'json': json,
            'io': __import__('io'),
            're': re
        }
        if name in safe_modules:
            return safe_modules[name]
        # Si intenta importar algo prohibido
        logger.warning(f"BLOCKED IMPORT: {name}")
        raise ImportError(f"La importación de '{name}' no está permitida en este entorno. Usa solo las herramientas pre-cargadas.")

    # Definir builtins restringidos
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
        'StopIteration': StopIteration,
        '__import__': restricted_import
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
        # Ejecutamos el código con el contexto restringido
        exec(clean_code, exec_globals, exec_globals)
        
        code_stdout = redirected_output.getvalue().strip()
        fig = exec_globals.get('fig', None)
        
        final_text = narrative
        if code_stdout:
            # Filtramos basura técnica que pandas suele tirar al stdout
            if not any(x in code_stdout.lower() for x in ["<class", "dtype:", "memory usage", "object at 0x"]):
                final_text += f"\n\n---\n{code_stdout}"
        
        return final_text, fig

    except KeyError as e:
        key_name = str(e).strip("'")
        # Solo reportamos como error de tabla si el error es en el nivel superior (context_obj)
        if isinstance(context_obj, dict) and key_name in context_obj.keys():
            # Este caso es raro (porque si existe no debería dar KeyError), pero por completitud:
            pass
        
        available_keys = list(context_obj.keys()) if isinstance(context_obj, dict) else "N/A"
        logger.error(f"KeyError: {e}. Available keys: {available_keys}")
        
        # Si el error parece ser una tabla mal referenciada
        if key_name in ["df", "dfs", "dataset", "table"]:
            return f"### ⚠️ Error de Estructura\nLa IA se confundió con el nombre del objeto de datos. Debe usar `{var_name}`.\n\n**Tablas disponibles:** `{available_keys}`", None
            
        return f"### ⚠️ Error de Referencia\nEl nombre `{e}` no se encontró en el contexto o en las tablas.\n\n**Tablas disponibles:** `{available_keys}`", None

    except ImportError as e:
        return f"### 🛡️ Restricción de Librería\n{str(e)}", None

    except Exception as e:
        logger.error(f"Execution Error: {e}")
        # Mensajes más amigables para errores comunes de Pandas
        err_str = str(e)
        if "not found in axis" in err_str:
             return f"### ⚠️ Columna no encontrada\nUna de las columnas mencionadas no existe en el archivo. Verifica los nombres exactos.", None
        
        return f"### ⚠️ Error en el Procesamiento\nHubo un problema ejecutando el análisis lógico solicitado.\n\n*Detalle técnico: {err_str}*", None
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
