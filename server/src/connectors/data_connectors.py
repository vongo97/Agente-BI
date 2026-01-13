import pandas as pd
from sqlalchemy import create_engine, inspect

# Cache en memoria para sesiones (Mantenemos simple para el MVP)
sql_engines = {}

def get_sql_engine(url):
    """Crea y devuelve el motor de SQLAlchemy."""
    if url not in sql_engines:
        sql_engines[url] = create_engine(url)
    return sql_engines[url]

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
    """Limpia los nombres de las columnas y prepara los datos numéricos."""
    df.columns = [c.strip() for c in df.columns]
    
    # Limpieza inteligente de columnas numéricas que vienen como strings con moneda
    for col in df.columns:
        if df[col].dtype == 'object':
            # Verificamos si parece una columna de dinero/unidades con formato
            sample = df[col].dropna().head(10).astype(str)
            if sample.str.contains(r'[€\$]').any():
                # Eliminamos símbolos y espacios
                cleaned = df[col].astype(str).str.replace(r'[€\$ ]', '', regex=True)
                # Manejamos el formato: Si hay comas y puntos, asumimos formato US (1,000.00)
                # Si solo hay comas, podría ser formato EU (1000,00). 
                # Por simplicidad para este caso: borrar comas (miles) y convertir
                cleaned = cleaned.str.replace(',', '')
                try:
                    df[col] = pd.to_numeric(cleaned)
                except:
                    pass
    return df

def load_file_data(file_path):
    """Carga archivos CSV o Excel y limpia los nombres de columnas."""
    ext = file_path.lower()
    try:
        if ext.endswith('.csv'):
            # Probar múltiples encodings para evitar errores de decodificación
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    print(f"[DEBUG] Archivo CSV cargado con éxito usando encoding: {encoding}")
                    return _clean_dataframe(df)
                except UnicodeDecodeError:
                    continue
            # Si ninguno funciona, dejar que lance el último error
            return _clean_dataframe(pd.read_csv(file_path))
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
