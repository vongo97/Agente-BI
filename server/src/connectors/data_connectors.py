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
    """Limpieza total y robusta para archivos financieros complejos."""
    import re
    import unicodedata

    def slugify_column(name):
        name = str(name).strip().replace('"', '').replace("'", "")
        name = "".join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
        name = re.sub(r'[^a-zA-Z0-9]', '_', name).lower()
        name = re.sub(r'_+', '_', name).strip('_')
        return name if name else "nan"

    # 1. Limpieza inicial: Eliminar todo lo que esté vacío
    df = df.dropna(how='all').dropna(axis=1, how='all')
    
    # 2. Localizar el Bloque de Datos y el Header
    if df.shape[0] > 1:
        # Buscamos la primera fila que tenga al menos un número o fecha
        for i in range(min(25, len(df))):
            # Usar vectorización para evitar errores de iteración en floats
            row_as_str = df.iloc[i].astype(str)
            if row_as_str.str.contains(r'\d').any():
                # Encontramos datos. Vamos a reconstruir el header fusionando las filas superiores
                header_rows = []
                for j in range(max(0, i-3), i):
                    header_rows.append(df.iloc[j].fillna("").astype(str).tolist())
                
                if header_rows:
                    final_headers = []
                    num_cols = df.shape[1]
                    for col_idx in range(num_cols):
                        # Unir piezas de texto de las filas de cabecera para esta columna
                        parts = [row[col_idx] for row in header_rows if row[col_idx].strip() and row[col_idx].lower() != 'nan']
                        full_name = " ".join(parts).strip()
                        final_headers.append(slugify_column(full_name))
                    
                    df.columns = final_headers
                else:
                    df.columns = [slugify_column(c) for c in df.iloc[i-1]]
                
                df = df.iloc[i:].reset_index(drop=True)
                break

    # 3. Forzar Nombres Únicos
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

    # 4. RESCATE DE FECHA (Prioridad Máxima)
    date_col_found = None
    for col in df.columns:
        sample = df[col].dropna().head(15)
        if not sample.empty:
            try:
                converted = pd.to_datetime(sample, errors='coerce')
                if converted.notnull().sum() > (len(sample) * 0.6):
                    if 'fecha' not in str(col).lower():
                        df = df.rename(columns={col: 'fecha_mes_ano'})
                        date_col_found = 'fecha_mes_ano'
                    else:
                        date_col_found = col
                    break
            except: pass

    # 5. Limpieza Numérica
    for col in df.columns:
        if col == date_col_found: continue
        try:
            col_data = df[col]
            if col_data.dtype == 'object':
                cleaned = col_data.astype(str).str.replace(r'[^-0-9,.]', '', regex=True).str.replace(',', '.')
                num_series = pd.to_numeric(cleaned, errors='coerce')
                if num_series.notnull().sum() > (len(df) * 0.4):
                    df[col] = num_series
        except: pass

    # 6. Eliminar columnas que se llamen 'nan' y que estén vacías
    cols_to_keep = [c for c in df.columns if 'nan' not in str(c).lower() or df[c].notnull().sum() > 0]
    df = df[cols_to_keep]
    
    # 7. Eliminar filas de Metadatos / Notas (Footers)
    if not df.empty:
        # Si una fila tiene una celda con más de 50 caracteres y el resto casi vacío, es una nota
        def is_metadata_note(row):
            text_cells = [str(val) for val in row if len(str(val)) > 50]
            # Si hay una celda muy larga y pocas celdas con datos reales
            return len(text_cells) >= 1 and row.count() <= 3
            
        mask = df.apply(is_metadata_note, axis=1)
        df = df[~mask].reset_index(drop=True)

    # 8. Si la primera fila es igual al header, la borramos
    if not df.empty:
        try:
            first_row = df.iloc[0].astype(str).str.lower().tolist()
            headers = [str(c).lower() for c in df.columns]
            matches = sum(1 for r, h in zip(first_row, headers) if h in r or r in h)
            if matches >= (len(df.columns) * 0.6):
                df = df.iloc[1:].reset_index(drop=True)
        except: pass

    return df

def load_file_data(file_path):
    """Carga archivos CSV o Excel con detección de encoding robusta."""
    ext = file_path.lower()
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
                            print(f"[DEBUG] EXITO: CSV ({sep}, {encoding}, {decimal})")
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
            print(f"[DEBUG] Cargando archivo Excel (Context-safe): {file_path}")
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
                        print(f"[DEBUG] Hoja '{sheet}': {cells_count} celdas.")
                        
                        if cells_count > max_cells:
                            max_cells = cells_count
                            best_df = temp_df
                    except Exception as sheet_err:
                        print(f"[DEBUG] Error leyendo hoja '{sheet}': {sheet_err}")
                        continue
            
            if best_df is not None:
                # Si leímos con header=None, _clean_dataframe se encargará de encontrar el header real
                return _clean_dataframe(best_df)
            else:
                raise Exception("El archivo Excel parece estar vacío.")
        else:
            # Motor de carga de CSV Ultra-Resiliente (Detección automática)
            print(f"[DEBUG] Cargando archivo CSV (Auto-Sense): {file_path}")
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
        print(f"[DEBUG] Error crítico cargando archivo: {str(e)}")
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
