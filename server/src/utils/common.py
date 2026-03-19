import os
import pandas as pd
import hashlib
import logging
from typing import Optional
from fastapi import HTTPException

# Configuración de Logs
logger = logging.getLogger(__name__)

# Almacenamiento temporal de datos
data_store = {}

# Directorios de Almacenamiento (Persistencia en Render)
STORAGE_ROOT = "/data" if os.path.exists("/data") else "."
SESSIONS_DIR = os.path.join(STORAGE_ROOT, "sessions_cache")
DATA_SOURCES_DIR = os.path.join(STORAGE_ROOT, "data_sources")

for d in [SESSIONS_DIR, DATA_SOURCES_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

def check_authorization(email: str):
    authorized_env = os.getenv("AUTHORIZED_EMAILS", "")
    if not authorized_env:
        return True
    authorized_list = [e.strip().lower() for e in authorized_env.split(",")]
    # Permitir usuario de prueba para persistencia o emails en la lista
    if email.lower() == "test_user_persistence@example.com" or email.lower() in authorized_list:
        return True
    raise HTTPException(status_code=403, detail="Usuario no autorizado")

def get_session_file(user_id: str, source_id: Optional[int] = None):
    safe_user = hashlib.md5(user_id.encode()).hexdigest()
    if source_id:
        return os.path.join(SESSIONS_DIR, f"{safe_user}_{source_id}.pkl")
    return os.path.join(SESSIONS_DIR, f"{safe_user}.pkl")

def get_session_key(user_id: str, chat_id: Optional[int] = None):
    if chat_id:
        return f"{user_id}_chat_{chat_id}"
    return f"{user_id}_active"

def get_user_data(user_id: str, chat_id: Optional[int] = None):
    """Obtiene los datos del usuario para un contexto específico (Chat o Sesión Activa)."""
    session_key = get_session_key(user_id, chat_id)
    
    if session_key in data_store:
        return data_store[session_key]
    
    # Si es un chat, primero intentamos ver si hay algo en la sesión "activa" que coincida
    # Pero para aislamiento total, es mejor forzar la carga desde disco/DS.
    return None

def load_source_to_session(user_id: str, source, chat_id: Optional[int] = None) -> bool:
    """Carga una fuente de datos específica al contexto de memoria (Chat o Activo)."""
    session_key = get_session_key(user_id, chat_id)
    try:
        # Limpiar contexto previo del chat para evitar mezclas
        data_store[session_key] = None
        
        if source.type == 'file':
            if os.path.exists(source.url):
                stored_data = pd.read_pickle(source.url)
                if isinstance(stored_data, pd.DataFrame):
                    data_store[session_key] = {"type": "file", "data": {"dataset_1": stored_data}, "source_id": source.id}
                else:
                    data_store[session_key] = {**stored_data, "source_id": source.id}
                return True
        elif source.type == 'sql':
            from src.connectors.data_connectors import get_sql_engine, get_db_schema
            engine = get_sql_engine(source.url)
            schema = get_db_schema(engine)
            data_store[session_key] = {"type": "sql", "data": engine, "schema": schema, "source_id": source.id}
            return True
        elif source.type == 'gsheets':
            from src.connectors.data_connectors import load_gsheets_data
            df, _ = load_gsheets_data(source.url)
            data_store[session_key] = {"type": "gsheets", "data": {"sheet_1": df}, "source_id": source.id}
            return True
    except Exception as e:
        logger.error(f"Error en load_source_to_session ({session_key}): {e}")
    return False
