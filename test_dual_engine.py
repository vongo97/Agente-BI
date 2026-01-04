import os
import pandas as pd
import sys

# Añadir el path del servidor para importar el motor
sys.path.append(os.path.abspath('server'))
from src.engine.bi_analyst import analyze_with_gemini, execute_analysis

# Configurar API Key (Usar la del usuario si está disponible o una de test)
API_KEY = os.environ.get("GEMINI_API_KEY")

def test_dual_thinking():
    if not API_KEY:
        print("Error: GEMINI_API_KEY no configurada.")
        return

    print("--- INICIANDO TEST DE PENSAMIENTO DUAL ---")
    
    # 1. Cargar datos
    df = pd.read_csv('j:/Automatizaciones/BI/BD PRUEBA.csv')
    query = "¿Cuál es el ticket promedio (total_order) de los pedidos ENTREGADOS?"
    
    print(f"Pregunta: {query}")
    print("Ejecutando motor...")
    
    # 2. Ejecutar análisis (Doble pase interno)
    raw_response = analyze_with_gemini(df, query, API_KEY, mode="file")
    
    # 3. Procesar salida
    final_text, fig = execute_analysis(df, raw_response, "df")
    
    print("\n--- RESULTADO FINAL DEL BOT ---")
    print(final_text)
    
    if fig:
        print("\n✅ Gráfico generado correctamente.")
    else:
        print("\n❌ No se generó gráfico.")

if __name__ == "__main__":
    test_dual_thinking()
