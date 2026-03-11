import os
import pandas as pd
import hashlib
import logging
from fastapi import HTTPException

# Configuración de Logs
logger = logging.getLogger(__name__)

# Almacenamiento temporal de datos
data_store = {}

# Directorio para sesiones (caché de datos)
SESSIONS_DIR = "sessions_cache"
if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)

def check_authorization(email: str):
    authorized_env = os.getenv("AUTHORIZED_EMAILS", "")
    if not authorized_env:
        return True
    authorized_list = [e.strip().lower() for e in authorized_env.split(",")]
    if email.lower() not in authorized_list:
        raise HTTPException(status_code=403, detail="Usuario no autorizado")
    return True

def get_session_file(user_id: str):
    safe_id = hashlib.md5(user_id.encode()).hexdigest()
    return os.path.join(SESSIONS_DIR, f"{safe_id}.pkl")

def get_user_data(user_id: str):
    """Obtiene los datos del usuario, buscándolos en memoria o cargándolos desde el disco."""
    if user_id in data_store:
        return data_store[user_id]
    
    cache_path = get_session_file(user_id)
    if os.path.exists(cache_path):
        try:
            stored_data = pd.read_pickle(cache_path)
            if isinstance(stored_data, pd.DataFrame):
                data_store[user_id] = {"type": "file", "data": {"dataset_1": stored_data}}
            else:
                data_store[user_id] = {"type": stored_data.get("type", "file"), "data": stored_data.get("data", {})}
            return data_store[user_id]
        except Exception as e:
            logger.error(f"Error restaurando sesión para {user_id}: {e}")
    return None
