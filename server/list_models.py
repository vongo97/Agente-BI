from dotenv import load_dotenv
load_dotenv()
import google.generativeai as genai
from src.database import SessionLocal, UserConfig

# Obtener API Key del usuario
db = SessionLocal()
config = db.query(UserConfig).filter(UserConfig.user_id == "invitado@agente-bi.local").first()
db.close()

# Intentar desde localStorage backup o env
import os
api_key = None
if config and config.gemini_key:
    api_key = config.gemini_key
else:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not api_key:
    # Leer de .env.local del cliente como último recurso
    try:
        with open("../client/.env.local", "r") as f:
            for line in f:
                if "GEMINI" in line.upper() or "GOOGLE" in line.upper():
                    print(f"Found in .env.local: {line.strip()}")
    except:
        pass
    print("NO API KEY FOUND. Please provide one.")
    print("Usage: set the GEMINI_API_KEY env var or configure it in the UI")
    exit(1)

print(f"Using API Key ending in: ...{api_key[-6:]}")
genai.configure(api_key=api_key)

print("\n=== Available Models (supporting generateContent) ===")
for model in genai.list_models():
    if "generateContent" in [m.name for m in model.supported_generation_methods] if hasattr(model, 'supported_generation_methods') else True:
        print(f"  {model.name}")
