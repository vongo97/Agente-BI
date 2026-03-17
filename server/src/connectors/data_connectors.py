import pandas as pd
from sqlalchemy import create_engine, inspect

# Cache en memoria para sesiones (Mantenemos simple para el MVP)
sql_engines = {}

from urllib.parse import quote_plus
import urllib.parse

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
        print(f"[DEBUG] Error parseando URL SQL cruda: {e}")
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
    """Limpia los nombres de las columnas y prepara los datos numéricos de forma robusta."""
    df.columns = [c.strip() for c in df.columns]
    
    for col in df.columns:
        if df[col].dtype == 'object':
            # Muestra para detectar si es una columna numérica "sucia"
            sample = df[col].dropna().head(10).astype(str)
            
            # Si contiene dígitos y caracteres no numéricos sospechosos (moneda, mojibake, espacios)
            if sample.str.contains(r'\d').any() and sample.str.contains(r'[€\$â\x82\xac\x80 \xa0,]').any():
                cleaned = df[col].astype(str)
                
                # 1. Eliminar símbolos de moneda y basura de encoding (â\x82¬ etc)
                cleaned = cleaned.str.replace(r'[€\$â\x82\xac\x80 \xa0]', '', regex=True)
                
                # 2. Normalizar separadores (Manejo de , y .)
                # Caso: 1.234,56 -> 1234.56
                # Caso: 1,234.56 -> 1234.56
                # Si tiene ambos, el último suele ser el decimal.
                # Pero la mayoría de CSVs de negocios locales usan coma para decimal.
                if cleaned.str.contains(r',').any() and cleaned.str.contains(r'\.').any():
                    # Borramos comas (asumiendo miles)
                    cleaned = cleaned.str.replace(',', '')
                elif cleaned.str.contains(r',').any():
                    # Solo comas -> Decimal europeo
                    cleaned = cleaned.str.replace(',', '.')
                
                # 3. Limpieza final: solo números, punto y signo menos
                cleaned = cleaned.str.replace(r'[^-0-9.]', '', regex=True)
                
                try:
                    df[col] = pd.to_numeric(cleaned, errors='coerce')
                except:
                    pass
    return df

def load_file_data(file_path):
    """Carga archivos CSV o Excel y limpia los nombres de columnas."""
    ext = file_path.lower()
    try:
        if ext.endswith('.csv'):
            # Probar múltiples encodings y separadores para evitar errores
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            separators = [',', ';', '\t']
            last_error = None
            
            for encoding in encodings:
                for sep in separators:
                    try:
                        print(f"[DEBUG] Intentando cargar CSV con encoding: {encoding} y sep: {sep}")
                        # Intentamos cargar con el separador específico
                        df = pd.read_csv(file_path, encoding=encoding, sep=sep)
                        
                        # Si solo hay una columna y el separador no es coma, probablemente el sep sea incorrecto
                        if len(df.columns) == 1 and sep != ',':
                            continue
                            
                        print(f"[DEBUG] EXITO: Archivo CSV cargado con encoding: {encoding} y sep: {sep}")
                        return _clean_dataframe(df)
                    except (UnicodeDecodeError, pd.errors.ParserError) as e:
                        last_error = e
                        continue
                
                # Intento final con el motor de python que intenta adivinar el separador
                try:
                    print(f"[DEBUG] Intento alternativo (engine='python') con encoding: {encoding}")
                    df = pd.read_csv(file_path, encoding=encoding, sep=None, engine='python', on_bad_lines='skip')
                    print(f"[DEBUG] EXITO: Archivo CSV cargado con motor python, encoding: {encoding}")
                    return _clean_dataframe(df)
                except:
                    continue
            
            # Si ninguno funciona, lanzar el último error con detalle
            error_msg = f"No se pudo leer el CSV. Asegúrate de que el formato sea correcto. Error técnico: {last_error}"
            print(f"[DEBUG] {error_msg}")
            raise Exception(error_msg)
        elif ext.endswith(('.xls', '.xlsx', '.xlsm')):
            return _clean_dataframe(pd.read_excel(file_path))
        else:
            # Intentar cargar como CSV por defecto si no tiene extensión conocida
            try:
                return _clean_dataframe(pd.read_csv(file_path))
            except:
                raise ValueError(f"Formato de archivo no soportado. Por favor, sube un CSV o Excel (.xlsx).")
    except Exception as e:
        raise Exception(f"Error al leer el archivo: {str(e)}")

import re
import requests

def load_gsheets_data(gs_url):
    """Carga datos de una URL pública de Google Sheets y limpia los nombres de columnas."""
    try:
        # Extraer Sheet ID usando regex
        match_id = re.search(r"/d/([a-zA-Z0-9-_]+)", gs_url)
        if not match_id:
            print(f"[DEBUG] No se encontró Sheet ID en: {gs_url}")
            return None
        
        sheet_id = match_id.group(1)
        
        # Extraer GID (pestaña) usando regex
        match_gid = re.search(r"gid=([0-9]+)", gs_url)
        gid = match_gid.group(1) if match_gid else "0"
        
        # Intentar con el formato export primero
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        print(f"[DEBUG] Intento 1 (Export): {csv_url}")
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        response = requests.get(csv_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            return _clean_dataframe(df)
        
        print(f"[DEBUG] Error {response.status_code} en Intento 1. Probando alternativa...")
        
        # Intento 2: Formato pub (Publicar en la web)
        pub_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/pub?output=csv&gid={gid}"
        print(f"[DEBUG] Intento 2 (Pub): {pub_url}")
        response = requests.get(pub_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            return _clean_dataframe(df)

        # Intento 3: Gviz Visualization API (Muy robusto para datos públicos)
        gviz_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}"
        print(f"[DEBUG] Intento 3 (Gviz): {gviz_url}")
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
        print(f"[DEBUG] Fallaron todos los intentos: {status}")
        raise Exception(help_msg.strip())
        
    except Exception as e:
        if "HTTP" in str(e) or "Google rechazó" in str(e):
            raise e
        print(f"[DEBUG] Excepción inesperada: {str(e)}")
        raise Exception(f"Error técnico al conectar con Google: {str(e)}")
