import sqlite3
import os

db_path = "test_bi.db"
# Probamos también con bi_agent.db por si acaso
db_files = ["test_bi.db", "bi_agent.db"]

def migrate():
    for db_file in db_files:
        if not os.path.exists(db_file):
            print(f"Base de datos {db_file} no encontrada. Saltando...")
            continue
            
        print(f"Migrando base de datos: {db_file}...")
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # 1. Agregar 'columns' a 'data_sources'
        try:
            cursor.execute("ALTER TABLE data_sources ADD COLUMN columns TEXT")
            print(f"✅ Columna 'columns' añadida a 'data_sources' en {db_file}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"ℹ️ La columna 'columns' ya existe en 'data_sources' ({db_file})")
            else:
                print(f"❌ Error al añadir 'columns': {e}")
                
        # 2. Agregar 'data_source_id' a 'chats'
        try:
            cursor.execute("ALTER TABLE chats ADD COLUMN data_source_id INTEGER REFERENCES data_sources(id)")
            print(f"✅ Columna 'data_source_id' añadida a 'chats' en {db_file}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"ℹ️ La columna 'data_source_id' ya existe en 'chats' ({db_file})")
            else:
                print(f"❌ Error al añadir 'data_source_id': {e}")
                
        conn.commit()
        conn.close()
        print(f"Migración de {db_file} finalizada.\n")

if __name__ == "__main__":
    migrate()
