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

def load_gsheets_data(gs_url):
    """Carga datos de una URL pública de Google Sheets y limpia los nombres de columnas."""
    try:
        if "/d/" in gs_url:
            sheet_id = gs_url.split("/d/")[1].split("/")[0]
            gid = "0"
            if "gid=" in gs_url:
                gid = gs_url.split("gid=")[1].split("&")[0].split("#")[0]
            
            # Usar formato export?format=csv que es más directo para pandas
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
            
            print(f"[DEBUG] Conectando a Google Sheets: {csv_url}")
            
            # Añadir timeout y headers para evitar bloqueos
            df = pd.read_csv(csv_url, storage_options={'User-Agent': 'Mozilla/5.0'})
            return _clean_dataframe(df)
        
        print(f"[DEBUG] URL de Google Sheets no válida: {gs_url}")
        return None
    except Exception as e:
        print(f"[DEBUG] Error en load_gsheets_data: {str(e)}")
        raise e
