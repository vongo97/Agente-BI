import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

# URL de tu backend en Render
BACKEND_URL = os.getenv("NEXT_PUBLIC_API_URL", "https://tu-app-en-render.onrender.com")

def keep_alive():
    print(f"🚀 Iniciando Keep-Alive para: {BACKEND_URL}")
    while True:
        try:
            response = requests.get(BACKEND_URL)
            if response.status_code == 200:
                print(f"✅ [PING] Servidor activo: {response.status_code}")
            else:
                print(f"⚠️ [PING] Respuesta inesperada: {response.status_code}")
        except Exception as e:
            print(f"❌ [PING] Error conectando al servidor: {e}")
        
        # Render entra en sleep a los 15 min. Pingeamos cada 14 min.
        time.sleep(14 * 60)

if __name__ == "__main__":
    keep_alive()
