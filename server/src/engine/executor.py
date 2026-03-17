import sys
import pandas as pd
import plotly.express as px
import numpy as np
import json
import re
import ast
import logging
from io import StringIO
from sqlalchemy import text

logger = logging.getLogger(__name__)

def validate_code_safety(code):
    """
    Analiza el AST del código para detectar patrones maliciosos o accesos prohibidos.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Error de sintaxis en el código generado: {e}")

    # Palabras clave y atributos prohibidos (para evitar escapes de sandbox)
    forbidden_attrs = {
        '__globals__', '__subclasses__', '__mro__', '__builtins__', 
        '__qualname__', '__module__', '__dict__', 'func_globals', 
        'func_code', 'gi_frame', 'gi_code'
    }
    
    forbidden_calls = {
        'eval', 'exec', 'open', 'breakpoint', 'input', 'help'
    }

    for node in ast.walk(tree):
        # 1. Bloquear acceso a atributos peligrosos (ej: obj.__globals__)
        if isinstance(node, ast.Attribute):
            if node.attr in forbidden_attrs:
                raise SecurityError(f"Acceso prohibido al atributo '{node.attr}'")
        
        # 2. Bloquear nombres prohibidos
        if isinstance(node, ast.Name):
            if node.id in forbidden_calls:
                 raise SecurityError(f"Uso prohibido de la función '{node.id}'")
        
        # 3. Bloquear llamadas directas a funciones prohibidas
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in forbidden_calls:
                    raise SecurityError(f"Llamada prohibida a '{node.func.id}'")

    return True

class SecurityError(Exception):
    """Excepción personalizada para bloqueos de seguridad."""
    pass

class SmartDataContext(dict):
    """
    Un diccionario inteligente que permite acceder a tablas mediante alias comunes
    y proporciona mensajes de error útiles si una tabla no existe.
    """
    def __init__(self, data_dict):
        super().__init__(data_dict)
        self.raw_data = data_dict
        # Alias automáticos si solo hay una tabla
        if len(data_dict) == 1:
            self.main_key = list(data_dict.keys())[0]
            self._aliases = {"ventas", "data", "df", "dataset", "table", "resultados"}
        else:
            self.main_key = None
            self._aliases = {}

    def __getitem__(self, key):
        # 1. Intento de acceso directo
        if key in self.raw_data:
            return self.raw_data[key]
        
        # 2. Intento vía alias (solo si hay una única tabla principal)
        if self.main_key and key.lower() in self._aliases:
            return self.raw_data[self.main_key]
        
        # 3. Fallo informativo
        available = list(self.raw_data.keys())
        msg = f"No existe la tabla '{key}'. "
        if self.main_key:
            msg += f"¿Quisiste decir '{self.main_key}'? (Puedes usar '{key}' como alias)."
        else:
            msg += f"Tablas disponibles: {available}"
        raise KeyError(msg)

def get_safe_environment(var_name=None, context_obj=None):
    """
    Construye un entorno de ejecución (globals) seguro y enriquecido.
    """
    real_import = __import__
    
    # Envolvemos el contexto en el mapeador inteligente
    smart_context = SmartDataContext(context_obj) if isinstance(context_obj, dict) else context_obj

    def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
        allowed_packages = {
            'pandas', 'pd', 'numpy', 'np', 'plotly', 'px', 'json', 're',
            'math', 'datetime', 'collections', 'itertools', 'io', 'six', 'pytz'
        }
        root_package = name.split('.')[0]
        if root_package in allowed_packages:
            return real_import(name, globals, locals, fromlist, level)
        
        raise ImportError(f"Librería '{name}' bloqueada por seguridad. Usa Pandas, Plotly o Datetime.")

    safe_builtins = {
        'print': print, 'range': range, 'len': len, 'enumerate': enumerate,
        'zip': zip, 'min': min, 'max': max, 'sum': sum, 'abs': abs,
        'round': round, 'int': int, 'float': float, 'str': str, 'bool': bool,
        'list': list, 'dict': dict, 'set': set, 'tuple': tuple,
        'sorted': sorted, 'reversed': reversed, 'any': any, 'all': all,
        'isinstance': isinstance, 'type': type, 'hasattr': hasattr,
        'getattr': getattr, 'dir': dir, 'next': next, 'iter': iter,
        'filter': filter, 'map': map,
        'Exception': Exception, 'ValueError': ValueError, 'TypeError': TypeError,
        'StopIteration': StopIteration, 'KeyError': KeyError, 'IndexError': IndexError,
        '__import__': restricted_import
    }

    env = {
        'pd': pd, 'px': px, 'np': np, 'json': json,
        '__builtins__': safe_builtins
    }
    
    if var_name:
        env[var_name] = smart_context
        
        # INYECCIÓN DE ALIAS AUTOMÁTICOS (Invisible Aliasing)
        # Si context_obj es un dict con una sola tabla, exponemos esa tabla directamente
        # como 'df', 'ventas', 'data' para máxima compatibilidad con alucinaciones de la IA.
        if isinstance(context_obj, dict) and len(context_obj) == 1:
            main_df = list(context_obj.values())[0]
            if isinstance(main_df, pd.DataFrame):
                env['df'] = main_df
                env['data'] = main_df
                env['table'] = main_df
                # Solo inyectar 'ventas' si parece ser de ventas (o por defecto si es la única)
                env['ventas'] = main_df
                
    return env

def execute_analysis(context_obj, raw_response, var_name):
    """
    Ejecuta el código generado en un sandbox AST con Smart Context.
    """
    narrative = re.sub(r"```python\n(.*?)```", "", raw_response, flags=re.DOTALL).strip()
    code_match = re.search(r"```python\n(.*?)```", raw_response, re.DOTALL)
    
    if not code_match:
        return narrative, None

    clean_code = code_match.group(1).replace(".show()", "")

    try:
        validate_code_safety(clean_code)
    except (SecurityError, ValueError) as e:
        return f"### 🛡️ Restricción de Seguridad\n{str(e)}", None

    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    exec_globals = get_safe_environment(var_name, context_obj)
    
    try:
        import threading
        
        def target():
            try:
                exec(clean_code, exec_globals, exec_globals)
            except Exception as e:
                exec_globals['__exec_exception__'] = e

        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout=10) # 10 segundos de timeout
        
        if thread.is_alive():
            return "### 🛡️ Tiempo Agotado\nEl análisis tomó demasiado tiempo (>10s) y fue abortado por seguridad.", None

        if '__exec_exception__' in exec_globals:
            raise exec_globals['__exec_exception__']
        
        code_stdout = redirected_output.getvalue().strip()
        fig = exec_globals.get('fig', None)
        
        final_text = narrative
        if code_stdout:
            # Filtramos solo si es basura técnica real
            if not any(x in code_stdout.lower() for x in ["<class", "memory usage", "object at 0x"]):
                final_text += f"\n\n---\n{code_stdout}"
        
        return final_text, fig

    except KeyError as e:
        # El SmartDataContext ya nos da un mensaje amigable
        error_msg = str(e).strip("'")
        return f"### ⚠️ Error de Estructura\n{error_msg}", None

    except ImportError as e:
        return f"### 🛡️ Restricción de Librería\n{str(e)}", None

    except Exception as e:
        logger.error(f"Execution Error: {e}")
        err_msg = str(e)
        if "not found in axis" in err_msg:
            err_msg = "Una de las columnas mencionadas no existe en el dataset."
        return f"### ⚠️ Error de Análisis\n{err_msg}", None
    finally:
        sys.stdout = old_stdout

def safe_exec_cleaning(df, code):
    """
    Ejecutor de limpieza con validación AST y Smart Env.
    """
    try:
        validate_code_safety(code)
    except Exception as e:
        return df, f"Bloqueo de seguridad: {e}"

    initial_rows = len(df)
    namespace = get_safe_environment("df", df.copy())
    
    try:
        exec(code, namespace, namespace)
        cleaned_df = namespace.get("df")
        summary = namespace.get("clean_summary", "Limpieza completada.")
        
        if len(cleaned_df) < initial_rows and len(cleaned_df) <= 5 and initial_rows > 10:
             return df, "Error: Truncado de datos detectado."
             
        return cleaned_df, summary
    except Exception as e:
        logger.error(f"Cleaning Error: {e}")
        raise e

def validate_sql_safety(sql_query):
    """
    Validación rigurosa para asegurar que solo se ejecutan sentencias SELECT.
    """
    query_upper = sql_query.upper().strip()
    
    if not query_upper.startswith("SELECT") and not query_upper.startswith("WITH"):
        raise SecurityError("La consulta debe ser de tipo SELECT o usar una cláusula WITH (CTE).")
        
    forbidden_keywords = [
        r'\bDROP\b', r'\bDELETE\b', r'\bUPDATE\b', r'\bINSERT\b', 
        r'\bALTER\b', r'\bTRUNCATE\b', r'\bEXEC\b', r'\bEXECUTE\b',
        r'\bGRANT\b', r'\bREVOKE\b', r'\bCREATE\b'
    ]
    
    for word in forbidden_keywords:
        if re.search(word, query_upper):
            raise SecurityError(f"Se detectó una palabra clave SQL prohibida por seguridad: {word.replace(r'\\b', '')}")
            
    return True

def execute_sql_safe(engine, raw_sql_response):
    """
    Parsea, valida y ejecuta una consulta SQL de forma segura.
    Devuelve un DataFrame de Pandas o un error seguro.
    """
    sql_match = re.search(r"```sql\n(.*?)```", raw_sql_response, re.DOTALL | re.IGNORECASE)
    if sql_match:
        clean_sql = sql_match.group(1).strip()
    else:
        clean_sql = raw_sql_response.strip().strip('`')
        
    try:
        validate_sql_safety(clean_sql)
    except SecurityError as e:
         return f"### 🛡️ Restricción de Seguridad SQL\n{str(e)}", None, None
         
    try:
        with engine.connect() as conn:
            df_result = pd.read_sql(text(clean_sql), conn)
            
        code_stdout = f"Resultados de la consulta SQL ({len(df_result)} filas):\n{df_result.to_string()}"
        return code_stdout, df_result, clean_sql
    except Exception as e:
        logger.error(f"Error ejecutando SQL: {e}")
        return f"### ⚠️ Error de Análisis SQL\n{e}", None, None
