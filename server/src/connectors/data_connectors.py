import logging
import re
import requests
import pandas as pd
from sqlalchemy import create_engine, inspect
from urllib.parse import quote_plus
import urllib.parse

logger = logging.getLogger(__name__)

# Cache en memoria para sesiones
sql_engines = {}

def clean_sql_url(url):
    """
    Soluciona el problema de SQLAlchemy cuando la contraseña contiene una '@'.
    Ejemplo problemático: postgresql://user:P@assword@host:5432/db
    """
    if "://" not in url or "@" not in url:
        return url
        
    try:
        parts = url.rsplit('@', 1)
        if len(parts) != 2: return url
        
        creds_part, host_part = parts
        scheme_parts = creds_part.split('://', 1)
        if len(scheme_parts) != 2: return url
        
        scheme, user_and_pass = scheme_parts
        up_parts = user_and_pass.split(':', 1)
        if len(up_parts) == 2:
            user, pwd = up_parts
            pwd_encoded = quote_plus(urllib.parse.unquote_plus(pwd))
            return f"{scheme}://{user}:{pwd_encoded}@{host_part}"
        elif len(up_parts) == 1:
            return url
    except Exception as e:
        logger.warning("Error parseando URL SQL: %s", type(e).__name__)
        return url
        
    return url

def get_sql_engine(url):
    """Crea y devuelve el motor de SQLAlchemy asegurando una URL limpia."""
    clean_url = clean_sql_url(url)
    
    if clean_url not in sql_engines:
        sql_engines[clean_url] = create_engine(clean_url)
    return sql_engines[clean_url]

def get_db_schema(engine):
    """Obtiene el esquema de la base de datos."""
    inspector = inspect(engine)
    schema_info = ""
    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        col_names = [col['name'] for col in columns]
        schema_info += f"Table: {table_name}, Columns: {col_names}\n"
    return schema_info

def _clean_dataframe(df):
    """Limpieza robusta con detección inteligente de header válido."""
    import unicodedata

    def slugify_column(name):
        name = str(name).strip().replace('"', '').replace("'", "")
        name = "".join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
        name = re.sub(r'[^a-zA-Z0-9]', '_', name).lower()
        name = re.sub(r'_+', '_', name).strip('_')
        return name if name else "nan"

    df = df.dropna(how='all').dropna(axis=1, how='all').reset_index(drop=True)
    if df.empty:
        return df

    cols_are_numeric = all(
        str(c).strip().lstrip('-').replace('.', '', 1).isdigit()
        for c in df.columns
    )

    if not cols_are_numeric:
        df.columns = [slugify_column(c) for c in df.columns]
    else:
        for i in range(min(10, len(df))):
            row_as_str = df.iloc[i].astype(str)
            if row_as_str.str.contains(r'[a-zA-Z]').any() and not row_as_str.str.match(r'^\d+\.?\d*$').all():
                header_data = df.iloc[i].fillna("").astype(str)
                df.columns = [slugify_column(c) for c in header_data]
                df = df.iloc[i + 1:].reset_index(drop=True)
                break

    cols = []
    seen = {}
    for c in df.columns:
        c_str = str(c)
        if c_str in seen:
            seen[c_str] += 1
            cols.append(f"{c_str}_{seen[c_str]}")
        else:
            seen[c_str] = 0
            cols.append(c_str)
    df.columns = cols

    for col in df.columns:
        if df[col].dtype == 'object':
            cleaned = df[col].astype(str).str.replace(r'[^-0-9,.]', '', regex=True).str.replace(',', '.')
            num_series = pd.to_numeric(cleaned, errors='coerce')
            if num_series.notnull().sum() > (len(df) * 0.5):
                df[col] = num_series

        if 'fecha' in col.lower() or 'date' in col.lower() or 'mes' in col.lower():
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except Exception:
                pass

    if not df.empty and len(df) > 1:
        def is_metadata_note(row):
            text_cells = [str(val) for val in row if len(str(val)) > 50]
            return len(text_cells) >= 1 and row.count() <= 3
        mask = df.apply(is_metadata_note, axis=1)
        df = df[~mask].reset_index(drop=True)

    return df

def load_file_data(file_path):
    """Carga archivos CSV o Excel con detección de encoding robusta."""
    import os
    ext = file_path.lower()
    basename = os.path.basename(file_path)  # Solo el nombre, nunca la ruta completa
    try:
        if ext.endswith('.csv'):
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            separators = [';', ',', '\t']
            
            for encoding in encodings:
                for sep in separators:
                    try:
                        decimal = ',' if sep == ';' else '.'
                        df = pd.read_csv(file_path, encoding=encoding, sep=sep, decimal=decimal)
                        if len(df.columns) > 1:
                            logger.debug("CSV cargado: file=%s sep=%r enc=%s", basename, sep, encoding)
                            return _clean_dataframe(df)
                    except:
                        continue
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, sep=None, engine='python', on_bad_lines='skip')
                    return _clean_dataframe(df)
                except: continue
                
            raise Exception("No se pudo determinar el formato del CSV.")

        elif ext.endswith(('.xls', '.xlsx', '.xlsm')):
            logger.debug("Cargando Excel: file=%s", basename)
            engine = 'openpyxl' if ext.endswith('.xlsx') else None
            
            best_df = None
            max_cells = -1
            
            with pd.ExcelFile(file_path, engine=engine) as excel_file:
                sheets = excel_file.sheet_names
                for sheet in sheets:
                    try:
                        temp_df = pd.read_excel(excel_file, sheet_name=sheet, header=None)
                        cells_count = temp_df.notnull().sum().sum()
                        logger.debug("Excel hoja=%r celdas=%d", sheet, cells_count)
                        
                        if cells_count > max_cells:
                            max_cells = cells_count
                            best_df = temp_df
                    except Exception as sheet_err:
                        logger.warning("Error leyendo hoja Excel sheet=%r: %s", sheet, type(sheet_err).__name__)
                        continue
            
            if best_df is not None:
                return _clean_dataframe(best_df)
            else:
                raise Exception("El archivo Excel parece estar vacío.")
        else:
            logger.debug("CSV auto-sense: file=%s", basename)
            encodings = ['utf-8-sig', 'latin-1', 'utf-8']
            best_df = None
            
            for enc in encodings:
                try:
                    best_df = pd.read_csv(file_path, sep=None, engine='python', encoding=enc)
                    if best_df.shape[1] > 1:
                        break
                except: continue
            
            if best_df is not None:
                return _clean_dataframe(best_df)
            else:
                return _clean_dataframe(pd.read_csv(file_path))

    except Exception as e:
        logger.error("Error cargando archivo file=%s: %s", basename, type(e).__name__)
        raise Exception(f"Error al leer el archivo: {type(e).__name__}")

def load_gsheets_data(gs_url):
    """Carga datos de una URL pública de Google Sheets y limpia los nombres de columnas."""
    try:
        match_id = re.search(r"/d/([a-zA-Z0-9-_]+)", gs_url)
        if not match_id:
            logger.warning("GSheets: Sheet ID no encontrado en URL.")
            return None
        
        sheet_id = match_id.group(1)
        match_gid = re.search(r"gid=([0-9]+)", gs_url)
        gid = match_gid.group(1) if match_gid else "0"
        
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; VektraBI/1.0)'}
        
        # Intento 1: Export CSV
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        logger.debug("GSheets: attempt=1 (export)")
        response = requests.get(csv_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            return _clean_dataframe(df)
        
        logger.debug("GSheets: attempt=1 falló status=%d", response.status_code)
        
        # Intento 2: Pub CSV
        pub_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/pub?output=csv&gid={gid}"
        logger.debug("GSheets: attempt=2 (pub)")
        response = requests.get(pub_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            return _clean_dataframe(df)

        # Intento 3: Gviz
        gviz_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}"
        logger.debug("GSheets: attempt=3 (gviz)")
        response = requests.get(gviz_url, headers=headers, timeout=10)

        if response.status_code == 200:
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            return _clean_dataframe(df)
            
        status = response.status_code
        logger.warning("GSheets: todos los intentos fallaron. status=%d", status)
        error_context = "Acceso Denegado (401/403)" if status in [401, 403] else f"Error {status}"
        
        help_msg = f"""
        Google rechazó la conexión ({error_context}). 
        
        Sigue estos pasos EXACTOS en tu Google Sheet:
        1. Botón 'Compartir' (arriba a la derecha).
        2. En 'Acceso general', cambia a 'Cualquier persona con el enlace'.
        3. Asegúrate de que diga 'Lector'.
        4. Copia el ENLACE de la barra de direcciones y pégalo aquí de nuevo.
        """
        raise Exception(help_msg.strip())
        
    except Exception as e:
        if "HTTP" in str(e) or "Google rechazó" in str(e):
            raise e
        logger.error("GSheets: excepción inesperada: %s", type(e).__name__)
        raise Exception("Error técnico al conectar con Google Sheets. Verifica que el documento sea público.")


def clean_sql_url(url):
    """
    Soluciona el problema de SQLAlchemy cuando la contraseña contiene una '@'.
    Ejemplo problemático: postgresql://user:P@assword@host:5432/db
    """
    if "://" not in url or "@" not in url:
        return url
        
    try:
        # Dividir por el ÚLTIMO '@' que separa credenciales del host
        parts = url.rsplit('@', 1)
        if len(parts) != 2: return url
        
        creds_part, host_part = parts
        
        # Separar el esquema (postgresql://) de las credenciales (user:pass)
        scheme_parts = creds_part.split('://', 1)
        if len(scheme_parts) != 2: return url
        
        scheme, user_and_pass = scheme_parts
        
        # Separar usuario de contraseña
        up_parts = user_and_pass.split(':', 1)
        if len(up_parts) == 2:
            user, pwd = up_parts
            # Codificar solo la contraseña
            pwd_encoded = quote_plus(urllib.parse.unquote_plus(pwd))
            return f"{scheme}://{user}:{pwd_encoded}@{host_part}"
        elif len(up_parts) == 1:
            # Sin contraseña
            return url
    except Exception as e:
        from src.database import sanitize_db_error
        logger.debug("Error parseando URL SQL cruda: %s", sanitize_db_error(str(e)))
        return url
        
    return url

def get_sql_engine(url):
    """Crea y devuelve el motor de SQLAlchemy asegurando una URL limpia."""
    clean_url = clean_sql_url(url)
    
    if clean_url not in sql_engines:
        sql_engines[clean_url] = create_engine(clean_url)
    return sql_engines[clean_url]

def get_db_schema(engine):
    """Obtiene el esquema de la base de datos."""
    inspector = inspect(engine)
    schema_info = ""
    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        col_names = [col['name'] for col in columns]
        schema_info += f"Table: {table_name}, Columns: {col_names}\n"
    return schema_info

def _clean_dataframe(df):
    """Limpieza robusta con detección inteligente de header válido."""
    import re
    import unicodedata

    def slugify_column(name):
        name = str(name).strip().replace('"', '').replace("'", "")
        name = "".join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
        name = re.sub(r'[^a-zA-Z0-9]', '_', name).lower()
        name = re.sub(r'_+', '_', name).strip('_')
        return name if name else "nan"

    # 1. Limpieza inicial: Eliminar filas/columnas vacías
    df = df.dropna(how='all').dropna(axis=1, how='all').reset_index(drop=True)
    if df.empty:
        return df

    # 2. Detección de Header:
    #    - Si las columnas actuales de pandas son strings con letras (caso CSV estándar con header),
    #      solo slugificamos y seguimos. NO tocamos las filas de datos.
    #    - Si las columnas son índices numéricos (0, 1, 2...) o son datos mezclados
    #      (Excel sin header), buscamos el header dentro de las filas.
    cols_are_numeric = all(
        str(c).strip().lstrip('-').replace('.', '', 1).isdigit()
        for c in df.columns
    )

    if not cols_are_numeric:
        # ✅ Caso normal: CSV con header correcto → solo normalizar nombres
        df.columns = [slugify_column(c) for c in df.columns]
    else:
        # 🔧 Caso Excel/CSV sin header: buscar la fila que actúa como cabecera
        for i in range(min(10, len(df))):
            row_as_str = df.iloc[i].astype(str)
            # La primera fila con texto puro (sin números) es el header
            if row_as_str.str.contains(r'[a-zA-Z]').any() and not row_as_str.str.match(r'^\d+\.?\d*$').all():
                header_data = df.iloc[i].fillna("").astype(str)
                df.columns = [slugify_column(c) for c in header_data]
                df = df.iloc[i + 1:].reset_index(drop=True)
                break

    # 3. Forzar Nombres Únicos (por si hay columnas duplicadas)
    cols = []
    seen = {}
    for c in df.columns:
        c_str = str(c)
        if c_str in seen:
            seen[c_str] += 1
            cols.append(f"{c_str}_{seen[c_str]}")
        else:
            seen[c_str] = 0
            cols.append(c_str)
    df.columns = cols

    # 4. Limpieza de datos: convertir columnas numéricas y de fecha
    for col in df.columns:
        if df[col].dtype == 'object':
            # Intentar conversión numérica
            cleaned = df[col].astype(str).str.replace(r'[^-0-9,.]', '', regex=True).str.replace(',', '.')
            num_series = pd.to_numeric(cleaned, errors='coerce')
            if num_series.notnull().sum() > (len(df) * 0.5):
                df[col] = num_series

        # Conversión de fecha por nombre de columna
        if 'fecha' in col.lower() or 'date' in col.lower() or 'mes' in col.lower():
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except Exception:
                pass

    # 5. Eliminar filas tipo "nota de pie" (texto largo en pocas celdas)
    if not df.empty and len(df) > 1:
        def is_metadata_note(row):
            text_cells = [str(val) for val in row if len(str(val)) > 50]
            return len(text_cells) >= 1 and row.count() <= 3
        mask = df.apply(is_metadata_note, axis=1)
        df = df[~mask].reset_index(drop=True)

    return df

def load_file_data(file_path):
    """Carga archivos CSV o Excel con detección de encoding robusta."""
    import os
    ext = file_path.lower()
    basename = os.path.basename(file_path)
    try:
        if ext.endswith('.csv'):
            # Latin-1 suele ser el culpable en archivos de Excel guardados como CSV en español
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            separators = [';', ',', '\t']
            
            for encoding in encodings:
                for sep in separators:
                    try:
                        decimal = ',' if sep == ';' else '.'
                        df = pd.read_csv(file_path, encoding=encoding, sep=sep, decimal=decimal)
                        
                        if len(df.columns) > 1:
                            logger.debug("CSV cargado con éxito (file=%s, sep=%r, enc=%s)", basename, sep, encoding)
                            return _clean_dataframe(df)
                    except:
                        continue
            
            # Último recurso: motor python
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, sep=None, engine='python', on_bad_lines='skip')
                    return _clean_dataframe(df)
                except: continue
                
            raise Exception("No se pudo determinar el formato del CSV.")
        elif ext.endswith(('.xls', '.xlsx', '.xlsm')):
            logger.debug("Cargando archivo Excel (Context-safe): file=%s", basename)
            engine = 'openpyxl' if ext.endswith('.xlsx') else None
            
            best_df = None
            max_cells = -1
            
            # Usar 'with' para asegurar que Windows libere el archivo inmediatamente
            with pd.ExcelFile(file_path, engine=engine) as excel_file:
                sheets = excel_file.sheet_names
                for sheet in sheets:
                    try:
                        # Leemos con header=None para no perder ninguna fila durante el conteo
                        temp_df = pd.read_excel(excel_file, sheet_name=sheet, header=None)
                        cells_count = temp_df.notnull().sum().sum()
                        logger.debug("Hoja '%s': %d celdas.", sheet, cells_count)
                        
                        if cells_count > max_cells:
                            max_cells = cells_count
                            best_df = temp_df
                    except Exception as sheet_err:
                        logger.debug("Error leyendo hoja '%s': %s", sheet, type(sheet_err).__name__)
                        continue
            
            if best_df is not None:
                # Si leímos con header=None, _clean_dataframe se encargará de encontrar el header real
                return _clean_dataframe(best_df)
            else:
                raise Exception("El archivo Excel parece estar vacío.")
        else:
            # Motor de carga de CSV Ultra-Resiliente (Detección automática)
            logger.debug("Cargando archivo CSV (Auto-Sense): file=%s", basename)
            encodings = ['utf-8-sig', 'latin-1', 'utf-8']
            best_df = None
            
            for enc in encodings:
                try:
                    # sep=None con engine='python' detecta automáticamente si es , ; o \t
                    best_df = pd.read_csv(file_path, sep=None, engine='python', encoding=enc)
                    if best_df.shape[1] > 1: # Si encontró más de una columna, es un éxito
                        break
                except: continue
            
            if best_df is not None:
                return _clean_dataframe(best_df)
            else:
                # Fallback final
                return _clean_dataframe(pd.read_csv(file_path))
    except Exception as e:
        logger.error("Error crítico cargando archivo file=%s: %s", basename, type(e).__name__)
        raise Exception(f"Error al leer el archivo: {type(e).__name__}")

import re
import requests

def load_gsheets_data(gs_url):
    """Carga datos de una URL pública de Google Sheets y limpia los nombres de columnas."""
    try:
        # Extraer Sheet ID usando regex
        match_id = re.search(r"/d/([a-zA-Z0-9-_]+)", gs_url)
        if not match_id:
            logger.warning("GSheets: Sheet ID no encontrado en URL.")
            return None
        
        sheet_id = match_id.group(1)
        
        # Extraer GID (pestaña) usando regex
        match_gid = re.search(r"gid=([0-9]+)", gs_url)
        gid = match_gid.group(1) if match_gid else "0"
        
        # Intentar con el formato export primero
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        logger.debug("GSheets: intentando export (attempt=1)")
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        response = requests.get(csv_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            return _clean_dataframe(df)
        
        logger.debug("GSheets: Intento 1 falló status=%d. Probando alternativa...", response.status_code)
        
        # Intento 2: Formato pub (Publicar en la web)
        pub_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/pub?output=csv&gid={gid}"
        logger.debug("GSheets: intentando pub (attempt=2)")
        response = requests.get(pub_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            return _clean_dataframe(df)

        # Intento 3: Gviz Visualization API (Muy robusto para datos públicos)
        gviz_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}"
        logger.debug("GSheets: intentando gviz (attempt=3)")
        response = requests.get(gviz_url, headers=headers, timeout=10)

        if response.status_code == 200:
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            return _clean_dataframe(df)
            
        # Si llegamos aquí, falló todo. Construir mensaje de ayuda específico.
        status = response.status_code
        error_context = "Acceso Denegado (401/403)" if status in [401, 403] else f"Error {status}"
        
        help_msg = f"""
        Google rechazó la conexión ({error_context}). 
        
        Sigue estos pasos EXACTOS en tu Google Sheet:
        1. Botón 'Compartir' (arriba a la derecha).
        2. En 'Acceso general', cambia a 'Cualquier persona con el enlace'.
        3. Asegúrate de que diga 'Lector'.
        4. Copia el ENLACE de la barra de direcciones y pégalo aquí de nuevo.
        """
        logger.debug("GSheets: fallaron todos los intentos con status=%d", status)
        raise Exception(help_msg.strip())
        
    except Exception as e:
        if "HTTP" in str(e) or "Google rechazó" in str(e):
            raise e
        logger.error("GSheets: excepción inesperada: %s", type(e).__name__)
        raise Exception("Error técnico al conectar con Google Sheets. Verifica que el documento sea público.")

