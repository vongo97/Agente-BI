import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY") or "TU_API_KEY_AQUI"

print(f"--- Diagnóstico de IA Vektra ---")
print(f"API Key detectada: {'SÍ' if api_key and 'TU_API_KEY' not in api_key else 'NO'}")

try:
    client = genai.Client(api_key=api_key)
    print("\nModelos disponibles:")
    for model in client.models.list():
        if "gemini" in model.name.lower():
            print(f"- {model.name} (Capacidad: {model.supported_generation_methods})")
            
    print("\nPrueba de generación:")
    response = client.models.generate_content(
        model="gemini-2.0-flash", # Probamos con el más estable actual
        contents="Hola, ¿estás listo para analizar datos?"
    )
    print(f"Respuesta IA: {response.text}")
    
except Exception as e:
    print(f"\n❌ ERROR CRÍTICO: {str(e)}")
