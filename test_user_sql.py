import sys
import os

# Asegurarse de que el directorio server está en el path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from sqlalchemy import text
from src.connectors.data_connectors import get_sql_engine, get_db_schema

def test_user_sql_connection():
    url = "postgresql://postgres:Ju@n21034579777@db.eraktxdfzxozuncrmhog.supabase.co:5432/postgres"
    print(f"Probando conexión a: {url.split('@')[1]}") # Print safe URL
    
    try:
        engine = get_sql_engine(url)
        with engine.connect() as conn:
            # Query simple para ver si conecta
            result = conn.execute(text("SELECT version();")).scalar()
            print(f"¡Conexión Exitosa!\nVersión de BD: {result}")
            
        print("\nExtrayendo esquema...")
        schema = get_db_schema(engine)
        print("--- Esquema Recolectado ---")
        if len(schema.strip()) == 0:
            print("(El esquema está vacío. ¿No hay tablas?)")
        else:
            print(schema)
            
    except Exception as e:
        print(f"ERROR conectando a PostgreSQL: {e}")

if __name__ == "__main__":
    test_user_sql_connection()
