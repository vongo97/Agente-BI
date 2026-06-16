import os
import sys
from dotenv import load_dotenv

# Cargar .env de server
load_dotenv()

# Agregar la ruta raíz al path para poder importar
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.src.database import SessionLocal, UserConfig
from server.src.utils.security import decrypt_key
from google import genai

def diagnose():
    print("=== DIAGNOSTICO DE CLAVES Y API GEMINI ===")
    
    # 1. Conectar a la DB y leer UserConfig
    db = SessionLocal()
    try:
        configs = db.query(UserConfig).all()
        print(f"Total de configuraciones en DB: {len(configs)}")
        for config in configs:
            print(f"Usuario: {config.user_id}")
            has_gemini = "SI" if config.gemini_key else "NO"
            print(f"  - ¿Tiene key Gemini?: {has_gemini}")
            if config.gemini_key:
                decrypted = decrypt_key(config.gemini_key)
                if decrypted:
                    print(f"  - Key descifrada con exito: {decrypted[:6]}...{decrypted[-4:]}")
                    
                    # Probar llamada
                    client = genai.Client(api_key=decrypted)
                    for model in ["gemini-3-flash-preview", "gemini-3.1-pro-preview", "gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash"]:
                        try:
                            resp = client.models.generate_content(model=model, contents="Responde OK")
                            print(f"    - {model}: EXITO ({resp.text.strip()})")
                        except Exception as e:
                            print(f"    - {model}: FALLO ({str(e)})")
                else:
                    print("  - ERROR: No se pudo descifrar (Encryption key desalineada)")
                
    except Exception as e:
        print(f"ERROR en diagnostico: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    diagnose()
