import sys
import os

# Asegurarse de que el directorio server está en el path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

import pandas as pd
from sqlalchemy import create_engine
from src.connectors.data_connectors import get_sql_engine, get_db_schema
from src.engine.bi_analyst import analyze_data

def setup_test_db():
    # Usar una base de datos en memoria o local para test
    db_path = 'sqlite:///test_sql_bi.db'
    engine = create_engine(db_path)
    
    # Proveer algo de data sintética
    df_clientes = pd.DataFrame({
        'id': [1, 2, 3],
        'nombre': ['Empresa A', 'StartUp B', 'Consultora C'],
        'tipo': ['Premium', 'Estandar', 'Premium']
    })
    df_ventas = pd.DataFrame({
        'id_venta': [101, 102, 103, 104],
        'id_cliente': [1, 1, 2, 3],
        'monto': [1500.50, 2300.00, 450.00, 3100.75],
        'fecha': ['2026-01-10', '2026-02-15', '2026-02-20', '2026-03-01']
    })
    
    df_clientes.to_sql('clientes', engine, if_exists='replace', index=False)
    df_ventas.to_sql('ventas', engine, if_exists='replace', index=False)
    return engine

def test_sql_agent():
    print("1. Configurando base de datos de prueba...")
    engine = setup_test_db()
    schema = get_db_schema(engine)
    print(f"Esquema recolectado:\n{schema}")
    
    context = {
        "type": "sql",
        "data": engine,
        "schema": schema
    }
    
    # Extraer la API KEY para la prueba
    from dotenv import load_dotenv
    load_dotenv("server/.env")
    api_key = os.environ.get("GOOGLE_API_KEY")
        
    if not api_key:
        print("ERROR: Necesitas GOOGLE_API_KEY en server/.env para probar esto.")
        return
        
    query = "¿Indícame cuál es la suma total de las ventas hechas exclusivamente a clientes de tipo 'Premium'?"
    print(f"\n2. Realizando pregunta a la IA: '{query}'")
    
    print("\n3. Lanzando el flujo Text-to-SQL + Estratega...")
    response = analyze_data(
        data_context=context,
        query=query,
        api_key=api_key,
        mode="sql"
    )
    
    print("\n--- Respuesta Final del Agente BI ---")
    print(response)

if __name__ == "__main__":
    test_sql_agent()
