import pandas as pd
import sys
import os
import json

# Configuración de rutas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'server')))
from src.engine import bi_analyst, executor

def test_multitable_joins():
    print("--- INICIANDO TEST DE SOPORTE MULTITABLA (JOINS) ---")
    
    # 1. Preparar datos de prueba
    df_ventas = pd.DataFrame({
        'pedido_id': [101, 102, 103, 104],
        'producto_id': [1, 2, 1, 3],
        'monto': [1200, 50, 1200, 300]
    })
    
    df_productos = pd.DataFrame({
        'id': [1, 2, 3],
        'nombre_comercial': ['Laptop Pro', 'Mouse Inalámbrico', 'Monitor 4K']
    })
    
    # Simular el contexto que prepararía el backend (resumen de tablas)
    context_schema = {
        'ventas': {
            'columns': df_ventas.columns.tolist(),
            'sample': df_ventas.head(2).to_dict()
        },
        'productos': {
            'columns': df_productos.columns.tolist(),
            'sample': df_productos.head(2).to_dict()
        }
    }
    
    # El contexto real de ejecución (DataFrames reales)
    dfs_real = {
        'ventas': df_ventas,
        'productos': df_productos
    }
    
    query = "¿Cuánto hemos vendido por cada nombre de producto? Cruza la tabla ventas con productos."
    print(f"Pregunta: {query}")
    
    # 2. Obtener análisis
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY no configurada.")
        return

    print("\nGenerando plan de análisis multitabla...")
    raw_response = bi_analyst.analyze_data(
        context_schema, 
        query, 
        api_key, 
        mode="file", 
        provider="gemini"
    )
    
    print("\n[IA Generó Código]:")
    # Extraer y mostrar el código para depuración
    import re
    code_match = re.search(r"```python\n(.*?)```", raw_response, re.DOTALL)
    if code_match:
        print(code_match.group(1))
    
    # 3. Ejecutar análisis (usando los DFs reales)
    print("\nEjecutando cruce de tablas...")
    final_text, fig = executor.execute_analysis(dfs_real, raw_response, "dfs")
    
    print("\n[RESULTADO]:")
    print(final_text)
    
    if fig:
        print("\n[OK] Gráfico generado correctamente tras el JOIN.")
    else:
        print("\n[ERROR] No se generó gráfico.")

if __name__ == "__main__":
    test_multitable_joins()
