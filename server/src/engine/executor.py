import sys
import os
import tempfile
import shutil
import subprocess
import pickle
import platform
import threading
import pandas as pd
import plotly.express as px
import numpy as np
import json
import re
import ast
import logging
import asyncio
from io import StringIO
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Semáforo global que limita a un máximo de 2 ejecuciones pesadas del sandbox en paralelo
execution_semaphore = asyncio.Semaphore(2)

# ──────────────────────────────────────────────────────────────────────────────
# LÍMITES DE RECURSOS DEL SANDBOX
# ──────────────────────────────────────────────────────────────────────────────
_SANDBOX_MEMORY_MB = 256          # Límite de RAM por proceso hijo (MB)
_SANDBOX_TIMEOUT_S  = 10          # Timeout de pared (segundos)
_SANDBOX_MAX_INPUT_BYTES = 50 * 1024 * 1024   # 50 MB máximo para pickle de entrada
_IS_LINUX = platform.system() == "Linux"

# Límites de tamaño de dataset (Meta C)
_MAX_TABLES  = 10
_MAX_COLUMNS = 300
_MAX_ROWS    = 500_000
_MAX_CELLS   = 1_000_000


def _make_preexec_linux(mem_mb: int, cpu_s: int):
    """
    Devuelve una función preexec_fn para subprocess.run que fija límites duros
    de RAM y CPU-time en el proceso hijo (solo Linux / Render).
    El kernel matará el proceso hijo si supera cualquiera de los límites.
    """
    def _set_limits():
        try:
            import resource
            mem_bytes = mem_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS,  (mem_bytes, mem_bytes))  # RAM virtual
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s + 2))      # CPU seconds
        except Exception:
            pass  # Si falla (permisos, etc.) continuamos sin límites duros
    return _set_limits


def _watchdog_windows(proc: subprocess.Popen, mem_mb: int, stop_event: threading.Event):
    """
    Hilo watchdog para Windows: mata el proceso hijo si supera `mem_mb` MB de RAM RSS.
    Se detiene sola cuando stop_event está seteado (proceso terminado).
    """
    try:
        import psutil
        ps_proc = psutil.Process(proc.pid)
        while not stop_event.is_set():
            try:
                rss_mb = ps_proc.memory_info().rss / (1024 * 1024)
                if rss_mb > mem_mb:
                    logger.warning("Sandbox OOM: proceso hijo superó %d MB (RSS=%.1f MB). Terminando.",
                                   mem_mb, rss_mb)
                    ps_proc.kill()
                    return
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return
            stop_event.wait(timeout=0.5)
    except ImportError:
        pass  # psutil no disponible; watchdog desactivado


def _run_subprocess_with_limits(cmd, env_clean, timeout=_SANDBOX_TIMEOUT_S):
    """
    Lanza cmd como subproceso con límites de recursos apropiados para la plataforma:
    - Linux: preexec_fn (setrlimit) para límites duros de RAM y CPU.
    - Windows: watchdog thread con psutil para límites blandos de RAM.
    Siempre aplica timeout de reloj de pared.
    """
    if _IS_LINUX:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env_clean,
            cwd=cmd[1].rsplit('/', 1)[0] if '/' in cmd[1] else None,  # cwd=temp_dir del script
            preexec_fn=_make_preexec_linux(_SANDBOX_MEMORY_MB, timeout + 2)
        )
    else:
        # Windows: iniciar con Popen + watchdog
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env_clean,
            cwd=os.path.dirname(cmd[1])   # cwd = temp_dir del script
        )
        stop_event = threading.Event()
        watchdog = threading.Thread(
            target=_watchdog_windows,
            args=(proc, _SANDBOX_MEMORY_MB, stop_event),
            daemon=True
        )
        watchdog.start()
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            raise
        finally:
            stop_event.set()
        # Emular CompletedProcess para compatibilidad con el código existente
        return subprocess.CompletedProcess(
            args=cmd, returncode=proc.returncode,
            stdout=stdout, stderr=stderr
        )

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
        # 1. Bloquear bucles while para evitar bucles infinitos y DoS
        if isinstance(node, ast.While):
            raise SecurityError("Uso prohibido de bucles 'while'. Utiliza bucles 'for' acotados.")
            
        # 2. Bloquear acceso a atributos peligrosos (ej: obj.__globals__)
        if isinstance(node, ast.Attribute):
            if node.attr in forbidden_attrs:
                raise SecurityError(f"Acceso prohibido al atributo '{node.attr}'")
        
        # 3. Bloquear nombres prohibidos
        if isinstance(node, ast.Name):
            if node.id in forbidden_calls:
                 raise SecurityError(f"Uso prohibido de la función '{node.id}'")
        
        # 4. Bloquear llamadas directas a funciones prohibidas
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
        if len(data_dict) == 1:
            self.main_key = list(data_dict.keys())[0]
            self._aliases = {"ventas", "data", "df", "dataset", "table", "resultados"}
        else:
            self.main_key = None
            self._aliases = {}

    def __getitem__(self, key):
        if key in self.raw_data:
            return self.raw_data[key]
        
        if self.main_key and key.lower() in self._aliases:
            return self.raw_data[self.main_key]
        
        import difflib
        available = list(self.raw_data.keys())

        # NUEVO: Búsqueda por prefijo (maneja '11_P1' vs '11_P1_regiones_top5_departamentos')
        key_lower = key.lower()
        prefix_matches = [
            k for k in available
            if k.lower().startswith(key_lower) or key_lower.startswith(k.lower())
        ]
        if prefix_matches:
            logger.info(f"Tabla '{key}' vinculada a '{prefix_matches[0]}' por prefijo.")
            return self.raw_data[prefix_matches[0]]

        # Fuzzy matching con cutoff reducido (era 0.8, ahora 0.5)
        matches = difflib.get_close_matches(key, available, n=1, cutoff=0.5)
        if matches:
            if matches[0].lower() != key.lower():
                logger.info(f"Tabla '{key}' vinculada a '{matches[0]}' por similitud.")
            return self.raw_data[matches[0]]
        
        # Fallback final: si solo hay una tabla en el pool, devolverla directamente
        if len(self.raw_data) == 1:
            only_key = list(self.raw_data.keys())[0]
            logger.info(f"Tabla '{key}' no encontrada. Usando única tabla disponible: '{only_key}'.")
            return self.raw_data[only_key]
        
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
    smart_context = SmartDataContext(context_obj) if isinstance(context_obj, dict) else context_obj

    def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
        allowed_packages = {
            'pandas', 'pd', 'numpy', 'np', 'plotly', 'px', 'json', 're',
            'math', 'datetime', 'collections', 'itertools', 'io', 'six', 'pytz',
            'scipy', 'statsmodels', 'matplotlib', 'plt', 'sklearn', 'stats',
            'pandas_datareader', 'textwrap', 'functools', 'operator',
            'decimal', 'fractions', 'random', 'string', 'copy',
            'warnings', 'numbers', 'statistics'
        }
        root_package = name.split('.')[0]
        if root_package in allowed_packages:
            return real_import(name, globals, locals, fromlist, level)
        raise ImportError(f"Librería '{name}' bloqueada por seguridad.")

    safe_builtins = {
        'print': print, 'range': range, 'len': len, 'enumerate': enumerate,
        'zip': zip, 'min': min, 'max': max, 'sum': sum, 'abs': abs,
        'round': round, 'int': int, 'float': float, 'str': str, 'bool': bool,
        'list': list, 'dict': dict, 'set': set, 'tuple': tuple,
        'sorted': sorted, 'reversed': reversed, 'any': any, 'all': all,
        'isinstance': isinstance, 'next': next, 'iter': iter,
        'filter': filter, 'map': map,
        'Exception': Exception, 'ValueError': ValueError, 'TypeError': TypeError,
        'StopIteration': StopIteration, 'KeyError': KeyError, 'IndexError': IndexError,
        '__import__': restricted_import
    }

    env = {
        'pd': pd, 'px': px, 'np': np, 'json': json,
        '__builtins__': safe_builtins
    }
    
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        env['plt'] = plt
        env['matplotlib'] = matplotlib
    except:
        pass
    
    if var_name:
        env[var_name] = smart_context
        if isinstance(context_obj, dict) and len(context_obj) > 0:
            first_key = list(context_obj.keys())[0]
            main_df = context_obj[first_key]
            if isinstance(main_df, pd.DataFrame):
                env['df'] = main_df
                env['data'] = main_df
                env['table'] = main_df
                if first_key.isidentifier():
                    env[first_key] = main_df
                
    if not hasattr(pd.DataFrame, 'applymap'):
        pd.DataFrame.applymap = pd.DataFrame.map
        
    return env

# Definir un directorio de almacenamiento temporal seguro en el espacio de trabajo
STORAGE_ROOT = "/data" if os.path.exists("/data") else "."
TEMP_SANDBOX_DIR = os.path.join(STORAGE_ROOT, "sandbox_temp")
if not os.path.exists(TEMP_SANDBOX_DIR):
    try:
        os.makedirs(TEMP_SANDBOX_DIR)
    except:
        pass

async def execute_analysis(context_obj, raw_response, var_name):
    """
    Ejecuta el código generado en un sandbox aislado mediante un subproceso de Python independiente.
    """
    narrative = re.sub(r"```python\n(.*?)```", "", raw_response, flags=re.DOTALL).strip()
    code_match = re.search(r"```python\n(.*?)```", raw_response, re.DOTALL)
    
    if not code_match:
        return narrative, None

    import textwrap
    clean_code = code_match.group(1).replace(".show()", "")
    clean_code = textwrap.dedent(clean_code).strip()

    try:
        validate_code_safety(clean_code)
    except Exception as e:
        return f"### 🛡️ Restricción de Seguridad\n{str(e)}", None

    # Crear directorio temporal único dentro del sandbox_temp
    if not os.path.exists(TEMP_SANDBOX_DIR):
        os.makedirs(TEMP_SANDBOX_DIR, exist_ok=True)
    temp_dir = tempfile.mkdtemp(dir=TEMP_SANDBOX_DIR)
    
    try:
        # 1. Serializar el contexto de datos (Tablas)
        tables_to_save = {}
        metadata_tables = {}
        if isinstance(context_obj, pd.DataFrame):
            tables_to_save["df"] = context_obj
        elif isinstance(context_obj, dict):
            raw_dict = getattr(context_obj, 'raw_data', context_obj)
            for k, v in raw_dict.items():
                if isinstance(v, pd.DataFrame):
                    tables_to_save[k] = v

        # Validar límites del dataset antes de serializar
        if len(tables_to_save) > _MAX_TABLES:
            return f"### ⚠️ Dataset demasiado grande\nMáximo {_MAX_TABLES} tablas permitidas (enviadas: {len(tables_to_save)}).", None
        for tname, tdf in tables_to_save.items():
            if len(tdf.columns) > _MAX_COLUMNS:
                return f"### ⚠️ Dataset demasiado grande\nLa tabla '{tname}' tiene {len(tdf.columns)} columnas (máx: {_MAX_COLUMNS}).", None
            if len(tdf) > _MAX_ROWS:
                return f"### ⚠️ Dataset demasiado grande\nLa tabla '{tname}' tiene {len(tdf):,} filas (máx: {_MAX_ROWS:,}).", None
            if len(tdf) * len(tdf.columns) > _MAX_CELLS:
                return f"### ⚠️ Dataset demasiado grande\nLa tabla '{tname}' supera 1 millón de celdas.", None
        for idx, (name, df) in enumerate(tables_to_save.items()):
            pkl_filename = f"table_{idx}.pkl"
            pkl_path = os.path.join(temp_dir, pkl_filename)
            df.to_pickle(pkl_path)
            metadata_tables[name] = pkl_filename

        # Guardar el código Python a ejecutar
        code_path = os.path.join(temp_dir, "user_code.py")
        with open(code_path, "w", encoding="utf-8") as f:
            f.write(clean_code)
            
        # Crear el script de orquestación run.py
        orchestrator_path = os.path.join(temp_dir, "run.py")
        
        orchestrator_code = f"""import os
import sys
import json
import pickle
from io import StringIO
import pandas as pd
import numpy as np
import plotly.express as px

temp_dir = {repr(temp_dir)}
metadata_tables = {repr(metadata_tables)}
var_name = {repr(var_name)}

class SmartDataContext(dict):
    def __init__(self, data_dict):
        super().__init__(data_dict)
        self.raw_data = data_dict
        if len(data_dict) == 1:
            self.main_key = list(data_dict.keys())[0]
            self._aliases = {{"ventas", "data", "df", "dataset", "table", "resultados"}}
        else:
            self.main_key = None
            self._aliases = {{}}

    def __getitem__(self, key):
        if key in self.raw_data:
            return self.raw_data[key]
        if self.main_key and key.lower() in self._aliases:
            return self.raw_data[self.main_key]
        import difflib
        available = list(self.raw_data.keys())
        key_lower = key.lower()
        prefix_matches = [
            k for k in available
            if k.lower().startswith(key_lower) or key_lower.startswith(k.lower())
        ]
        if prefix_matches:
            return self.raw_data[prefix_matches[0]]
        matches = difflib.get_close_matches(key, available, n=1, cutoff=0.5)
        if matches:
            return self.raw_data[matches[0]]
        if len(self.raw_data) == 1:
            return self.raw_data[list(self.raw_data.keys())[0]]
        raise KeyError(f"No existe la tabla '{{key}}'. Tablas disponibles: {{available}}")

def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
    allowed_packages = {{
        'pandas', 'pd', 'numpy', 'np', 'plotly', 'px', 'json', 're',
        'math', 'datetime', 'collections', 'itertools', 'io', 'six', 'pytz',
        'scipy', 'statsmodels', 'matplotlib', 'plt', 'sklearn', 'stats',
        'pandas_datareader', 'textwrap', 'functools', 'operator',
        'decimal', 'fractions', 'random', 'string', 'copy',
        'warnings', 'numbers', 'statistics'
    }}
    root_package = name.split('.')[0]
    if root_package in allowed_packages:
        return __import__(name, globals, locals, fromlist, level)
    raise ImportError(f"Librer\u00eda '{{name}}' bloqueada por seguridad.")

safe_builtins = {{
    'print': print, 'range': range, 'len': len, 'enumerate': enumerate,
    'zip': zip, 'min': min, 'max': max, 'sum': sum, 'abs': abs,
    'round': round, 'int': int, 'float': float, 'str': str, 'bool': bool,
    'list': list, 'dict': dict, 'set': set, 'tuple': tuple,
    'sorted': sorted, 'reversed': reversed, 'any': any, 'all': all,
    'isinstance': isinstance, 'next': next, 'iter': iter,
    'filter': filter, 'map': map,
    'Exception': Exception, 'ValueError': ValueError, 'TypeError': TypeError,
    'StopIteration': StopIteration, 'KeyError': KeyError, 'IndexError': IndexError,
    '__import__': restricted_import
}}

env = {{
    'pd': pd, 'px': px, 'np': np, 'json': json,
    '__builtins__': safe_builtins
}}

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    env['plt'] = plt
    env['matplotlib'] = matplotlib
except:
    pass

loaded_tables = {{}}
for name, pkl_file in metadata_tables.items():
    with open(os.path.join(temp_dir, pkl_file), "rb") as f:
        loaded_tables[name] = pickle.load(f)

smart_context = SmartDataContext(loaded_tables)

if var_name:
    env[var_name] = smart_context
    if len(loaded_tables) > 0:
        first_key = list(loaded_tables.keys())[0]
        main_df = loaded_tables[first_key]
        if isinstance(main_df, pd.DataFrame):
            env['df'] = main_df
            env['data'] = main_df
            env['table'] = main_df
            if first_key.isidentifier():
                env[first_key] = main_df

if not hasattr(pd.DataFrame, 'applymap'):
    pd.DataFrame.applymap = pd.DataFrame.map

old_stdout = sys.stdout
redirected_output = sys.stdout = StringIO()

output_data = {{
    "success": False,
    "stdout": "",
    "analysis_text": None,
    "fig_json": None,
    "error": None,
    "error_type": None
}}

try:
    with open(os.path.join(temp_dir, "user_code.py"), "r", encoding="utf-8") as f:
        code_to_exec = f.read()
        
    exec(code_to_exec, env, env)
    
    output_data["success"] = True
    output_data["stdout"] = redirected_output.getvalue().strip()
    
    fig = env.get('fig', None)
    if fig and hasattr(fig, 'to_json'):
        output_data["fig_json"] = json.loads(fig.to_json())
    else:
        output_data["fig_json"] = fig
        
    analysis_text_var = env.get('analysis_text', None)
    if analysis_text_var:
        output_data["analysis_text"] = str(analysis_text_var).strip()
        
except Exception as e:
    output_data["success"] = False
    output_data["error"] = str(e)
    output_data["error_type"] = type(e).__name__
finally:
    sys.stdout = old_stdout

with open(os.path.join(temp_dir, "output.json"), "w", encoding="utf-8") as f:
    json.dump(output_data, f)
"""
        with open(orchestrator_path, "w", encoding="utf-8") as f:
            f.write(orchestrator_code)

        # 3. Invocar al subproceso con entorno mínimo + límites de recursos
        # 3. Invocar al subproceso con entorno mínimo pero conservando paths de sistema
        # Esto es vital para Render donde PYTHONPATH, VIRTUAL_ENV y LD_LIBRARY_PATH son necesarios
        env_clean = os.environ.copy()
        env_clean["PYTHONIOENCODING"] = "utf-8"
        env_clean["MPLBACKEND"] = "Agg"
        
        # Ocultar secretos del entorno del sandbox por seguridad
        sensitive_keys = [
            "DATABASE_URL", "DIRECT_URL", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", 
            "ENCRYPTION_KEY", "AUTH_SECRET", "GEMINI_API_KEY", "MISTRAL_API_KEY", 
            "OPENAI_API_KEY", "ANTHROPIC_API_KEY"
        ]
        for k in sensitive_keys:
            if k in env_clean:
                del env_clean[k]

        async with execution_semaphore:
            result = await asyncio.to_thread(
                _run_subprocess_with_limits,
                [sys.executable, orchestrator_path],
                env_clean,
                timeout=_SANDBOX_TIMEOUT_S
            )

        # 4. Procesar resultado — stderr NUNCA se expone al usuario
        output_path = os.path.join(temp_dir, "output.json")
        if not os.path.exists(output_path):
            stderr_len = len(result.stderr.strip()) if result.stderr else 0
            logger.error("Sandbox: output.json ausente. returncode=%d stderr_len=%d",
                         result.returncode, stderr_len)
            return "### ⚠️ Error de Sandbox\nEl análisis no pudo completarse de forma segura. Por favor revisa el código generado.", None
            
        with open(output_path, "r", encoding="utf-8") as f:
            output_data = json.load(f)
            
        if not output_data["success"]:
            err_type = output_data["error_type"]
            err_msg = output_data["error"]
            if err_type == "KeyError":
                return f"### ⚠️ Error de Estructura\n{err_msg}", None
            else:
                return f"### ⚠️ Error de Análisis\n{err_msg}", None
                
        code_stdout = output_data["stdout"]
        fig = output_data["fig_json"]
        analysis_text_var = output_data["analysis_text"]
        
        final_text = narrative
        if analysis_text_var and str(analysis_text_var).strip():
            at_str = str(analysis_text_var).strip()
            if not any(x in at_str.lower() for x in ["<class", "memory usage", "object at 0x"]):
                final_text += f"\n\n---\n{at_str}"
        elif code_stdout:
            if not any(x in code_stdout.lower() for x in ["<class", "memory usage", "object at 0x"]):
                final_text += f"\n\n---\n{code_stdout}"
                
        return final_text, fig

    except subprocess.TimeoutExpired:
        logger.error("Timeout de Sandbox de ejecución.")
        return "### 🛡️ Tiempo Agotado\nEl análisis tomó demasiado tiempo (>10s) y fue abortado por seguridad.", None
    except Exception as e:
        logger.error(f"Fallo en Sandbox del ejecutor: {e}", exc_info=True)
        return f"### ⚠️ Error del Sandbox\nOcurrió un error inesperado al orquestar el entorno aislado: {str(e)}", None
    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as cleanup_err:
            logger.error(f"Error limpiando directorio temporal del sandbox: {cleanup_err}")

def safe_exec_cleaning(df, code):
    """
    Ejecuta el código de limpieza de datos en un subproceso Python aislado.
    """
    try:
        validate_code_safety(code)
    except Exception as e:
        return df, f"Bloqueo de seguridad: {e}"

    initial_rows = len(df)
    
    if not os.path.exists(TEMP_SANDBOX_DIR):
        os.makedirs(TEMP_SANDBOX_DIR, exist_ok=True)
    temp_dir = tempfile.mkdtemp(dir=TEMP_SANDBOX_DIR)
    
    try:
        # Serializar dataframe de entrada con validación de tamaño máximo
        input_pkl_path = os.path.join(temp_dir, "input_df.pkl")
        df.to_pickle(input_pkl_path)
        input_size = os.path.getsize(input_pkl_path)
        if input_size > _SANDBOX_MAX_INPUT_BYTES:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return df, f"Error: El dataset es demasiado grande para el sandbox ({input_size // (1024*1024)} MB > {_SANDBOX_MAX_INPUT_BYTES // (1024*1024)} MB máximo)."
        
        # Guardar código de limpieza
        code_path = os.path.join(temp_dir, "clean_code.py")
        with open(code_path, "w", encoding="utf-8") as f:
            f.write(code)
            
        # Crear script orquestador para la limpieza
        orchestrator_path = os.path.join(temp_dir, "run_clean.py")
        orchestrator_code = f"""import os
import sys
import json
import pickle
import pandas as pd
import numpy as np

temp_dir = {repr(temp_dir)}

with open(os.path.join(temp_dir, "input_df.pkl"), "rb") as f:
    df_load = pickle.load(f)

def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
    allowed_packages = {{
        'pandas', 'pd', 'numpy', 'np', 'json', 're',
        'math', 'datetime', 'collections', 'itertools', 'copy'
    }}
    root_package = name.split('.')[0]
    if root_package in allowed_packages:
        return __import__(name, globals, locals, fromlist, level)
    raise ImportError(f"Librer\u00eda '{{name}}' bloqueada por seguridad.")

safe_builtins = {{
    'print': print, 'range': range, 'len': len, 'enumerate': enumerate,
    'zip': zip, 'min': min, 'max': max, 'sum': sum, 'abs': abs,
    'round': round, 'int': int, 'float': float, 'str': str, 'bool': bool,
    'list': list, 'dict': dict, 'set': set, 'tuple': tuple,
    'isinstance': isinstance, 'next': next, 'iter': iter,
    'Exception': Exception, 'ValueError': ValueError, 'TypeError': TypeError,
    'KeyError': KeyError, 'IndexError': IndexError,
    '__import__': restricted_import
}}

env = {{
    'df': df_load,
    'pd': pd,
    'np': np,
    '__builtins__': safe_builtins
}}

output_data = {{
    "success": False,
    "clean_summary": "Limpieza completada.",
    "error": None
}}

try:
    with open(os.path.join(temp_dir, "clean_code.py"), "r", encoding="utf-8") as f:
        code_to_exec = f.read()
        
    exec(code_to_exec, env, env)
    
    cleaned_df = env.get("df")
    clean_summary = env.get("clean_summary", "Limpieza completada.")
    
    with open(os.path.join(temp_dir, "output_df.pkl"), "wb") as f:
        pickle.dump(cleaned_df, f)
        
    output_data["success"] = True
    output_data["clean_summary"] = str(clean_summary)
except Exception as e:
    output_data["success"] = False
    output_data["error"] = str(e)

with open(os.path.join(temp_dir, "output.json"), "w", encoding="utf-8") as f:
    json.dump(output_data, f)
"""
        with open(orchestrator_path, "w", encoding="utf-8") as f:
            f.write(orchestrator_code)

        # Ejecutar subproceso con entorno mínimo por plataforma
        if _IS_LINUX:
            env_clean = {
                "PATH": os.environ.get("PATH", ""),
                "PYTHONIOENCODING": "utf-8",
                "MPLBACKEND": "Agg",
            }
        else:
            env_clean = {
                "PATH": os.environ.get("PATH", ""),
                "PYTHONIOENCODING": "utf-8",
                "MPLBACKEND": "Agg",
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
                "TEMP": os.environ.get("TEMP", ""),
                "TMP": os.environ.get("TMP", ""),
            }

        result = _run_subprocess_with_limits(
            [sys.executable, orchestrator_path],
            env_clean,
            timeout=_SANDBOX_TIMEOUT_S
        )

        output_path = os.path.join(temp_dir, "output.json")
        if not os.path.exists(output_path):
            stderr_len = len(result.stderr.strip()) if result.stderr else 0
            logger.error("Sandbox clean: output.json ausente. returncode=%d stderr_len=%d",
                         result.returncode, stderr_len)
            return df, "Error de Sandbox: Fallo en ejecución aislada."
            
        with open(output_path, "r", encoding="utf-8") as f:
            output_data = json.load(f)
            
        if not output_data["success"]:
            return df, f"Error de Análisis: {output_data['error']}"
            
        # Deserializar df limpio
        output_pkl_path = os.path.join(temp_dir, "output_df.pkl")
        with open(output_pkl_path, "rb") as f:
            cleaned_df = pickle.load(f)
            
        summary = output_data["clean_summary"]
        
        if len(cleaned_df) < initial_rows and len(cleaned_df) <= 5 and initial_rows > 10:
             return df, "Error: Truncado de datos detectado."
             
        return cleaned_df, summary
        
    except subprocess.TimeoutExpired:
        logger.error("Timeout de Sandbox de limpieza.")
        return df, "Error de Sandbox: Tiempo de ejecución excedido (>10s)."
    except Exception as e:
        logger.error(f"Fallo en Sandbox de limpieza: {e}", exc_info=True)
        return df, f"Error de Sandbox inesperado: {str(e)}"
    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as cleanup_err:
            logger.error(f"Error limpiando directorio temporal de sandbox de limpieza: {cleanup_err}")

def validate_sql_safety(sql_query):
    query_upper = sql_query.upper().strip()
    if not query_upper.startswith("SELECT") and not query_upper.startswith("WITH"):
        raise SecurityError("La consulta debe ser de tipo SELECT.")
    
    forbidden = [r'\bDROP\b', r'\bDELETE\b', r'\bUPDATE\b', r'\bINSERT\b', r'\bALTER\b']
    for word in forbidden:
        if re.search(word, query_upper):
            raise SecurityError(f"Palabra prohibida: {word}")
    return True

def execute_sql_safe(engine, raw_sql_response):
    sql_match = re.search(r"```sql\n(.*?)```", raw_sql_response, re.DOTALL | re.IGNORECASE)
    clean_sql = sql_match.group(1).strip() if sql_match else raw_sql_response.strip().strip('`')
    
    try:
        validate_sql_safety(clean_sql)
        with engine.connect() as conn:
            df_result = pd.read_sql(text(clean_sql), conn)
        return f"Resultados ({len(df_result)} filas):\n{df_result.to_string()}", df_result, clean_sql
    except Exception as e:
        return f"### ⚠️ Error SQL\n{e}", None, None
