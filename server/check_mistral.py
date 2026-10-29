import os
try:
    # 1.x expone Mistral en la raíz; 2.x en mistralai.client
    try:
        from mistralai import Mistral
    except ImportError:
        from mistralai.client import Mistral
    print("✅ Librería mistralai cargada correctamente.")
except ImportError:
    print("❌ Librería mistralai NO encontrada.")
    exit()

# Intentamos usar la llave que el usuario debería tener (la buscaremos en el entorno o manual)
api_key = "TU_MISTRAL_KEY_AQUI" 

try:
    client = Mistral(api_key=api_key)
    print("Intentando saludo con Mistral...")
    resp = client.chat.complete(
        model="mistral-large-latest",
        messages=[{"role": "user", "content": "Hola"}]
    )
    print(f"Respuesta Mistral: {resp.choices[0].message.content}")
except Exception as e:
    print(f"❌ ERROR EN MISTRAL: {e}")
