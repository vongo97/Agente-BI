import sys
import os
import urllib.parse
from sqlalchemy import text
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))
from src.connectors.data_connectors import get_sql_engine, get_db_schema

def test_supabase():
    # El usuario dio: postgresql://postgres:Ju@n21034579777@db.eraktxdfzxozuncrmhog.supabase.co:5432/postgres
    # El password es Ju@n21034579777 . El @ rompe el parsing en sqlalchemy.
    encoded_pass = urllib.parse.quote_plus("Ju@n21034579777")
    url = f"postgresql://postgres:{encoded_pass}@db.eraktxdfzxozuncrmhog.supabase.co:5432/postgres"
    
    print(f"URL Segura (Oculta): postgresql://postgres:****@{url.split('@')[-1]}")
    
    try:
        engine = get_sql_engine(url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();")).scalar()
            print(f"\n[EXITO] Conectado a: {result}")
            
        print("\nExtrayendo esquema de la BD...")
        schema = get_db_schema(engine)
        print("======== ESQUEMA ========")
        print(schema)
        
    except Exception as e:
        print(f"\n[ERROR] Falló la conexión: {e}")

if __name__ == "__main__":
    test_supabase()
