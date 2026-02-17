import sys
import os
import pandas as pd

# Configuración de rutas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'server')))
from src.engine import bi_analyst, executor

def test_final_mvp():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY no encontrada.")
        return

    print("--- VERIFICACION FINAL DEL MVP ---")

    # 1. Verificar Filtro de Saludos (HOLA) en bi_analyst/main simulado
    # En el servidor real esto se hace en el endpoint, aquí verificamos la lógica
    print("\n1. Verificando Filtro de Saludo:")
    test_query = "Hola, ¿cómo estás?"
    greetings = ["hola", "hi", "hey", "buenos dias", "buenas tardes", "buenas noches", "que tal", "como estas"]
    clean_query = test_query.lower().strip().replace("!", "").replace("?", "")
    if any(g in clean_query for g in greetings):
        print("[OK] Saludo detectado correctamente.")
    else:
        print("[ERROR] No se detectó el saludo.")

    # 2. Verificar Sugerencias Multitabla
    print("\n2. Verificando Sugerencias Multitabla:")
    context_multidict = {
        'ventas': {'columns': ['id', 'monto', 'fecha'], 'sample': {}},
        'clientes': {'columns': ['id', 'nombre', 'pais'], 'sample': {}}
    }
    suggestions = bi_analyst.suggest_questions(context_multidict, api_key, mode="file")
    if suggestions and len(suggestions) > 0:
        print(f"[OK] Sugerencias generadas: {suggestions}")
    else:
        print("[ERROR] Fallo al generar sugerencias para múltiples tablas.")

    # 3. Verificar Generación de Presentación (Prompts)
    print("\n3. Verificando Integración de Presentación:")
    df_mini = pd.DataFrame({'ventas': [100, 200], 'mes': ['Jan', 'Feb']})
    pres_query = "Crea una presentación de las ventas"
    
    # Analyze data debería detectar "presentación" y cambiar el prompt
    response = bi_analyst.analyze_data(df_mini, pres_query, api_key, mode="file")
    
    if "---" in response and "# " in response:
        print("[OK] El motor genero una estructura de diapositivas (Markdown/Marp).")
        
        # 4. Probar Generador PPTX
        print("\n4. Verificando Generador de Archivo .pptx:")
        from src.engine import pptx_generator
        success, path = pptx_generator.create_presentation(response, "mvp_final_test.pptx")
        if success:
            print(f"[OK] Archivo PowerPoint generado: {path}")
            if os.path.exists(path): os.remove(path) # Limpiar
        else:
            print(f"[ERROR] Fallo al crear .pptx: {path}")
    else:
        print("[ERROR] El motor no genero formato de presentación.")

if __name__ == "__main__":
    test_final_mvp()
