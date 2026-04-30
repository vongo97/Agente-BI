from dotenv import load_dotenv
load_dotenv()
from src.database import SessionLocal, UserConfig

db = SessionLocal()
config = db.query(UserConfig).filter(UserConfig.user_id == "invitado@agente-bi.local").first()
if config:
    print(f"Key exists: {bool(config.gemini_key)}")
    if config.gemini_key:
        print(f"Key ends: ...{config.gemini_key[-6:]}")
    else:
        print("Gemini key is EMPTY/NULL")
else:
    print("No UserConfig found for this user!")
db.close()
