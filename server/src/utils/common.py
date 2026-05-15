import os
import pandas as pd
import hashlib
import logging
from typing import Optional
from fastapi import HTTPException
from src.utils.supabase_storage import sync_cloud_to_local, upload_file_to_cloud

# Configuración de Logs
logger = logging.getLogger(__name__)

# Almacenamiento temporal de datos
data_store = {}

# --- UTILIDADES DE SERIALIZACIÓN SEGURA ---
import json
from datetime import datetime, date
import numpy as np

class SafeJSONEncoder(json.JSONEncoder):
    """Codificador JSON que maneja fechas y tipos de numpy automáticamente."""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        if isinstance(obj, (np.float64, np.float32, np.float16)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

def json_serializable(obj):
    """Convierte un objeto a un diccionario serializable a JSON usando el encoder seguro."""
    return json.loads(json.dumps(obj, cls=SafeJSONEncoder))

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
        file_path = os.path.join(SESSIONS_DIR, f"{safe_user}_{source_id}.pkl")
    else:
        file_path = os.path.join(SESSIONS_DIR, f"{safe_user}.pkl")
    
    # Intentar traer de la nube si no está
    sync_cloud_to_local(file_path)
    return file_path

def get_session_key(user_id: str, chat_id: Optional[int] = None):
    if chat_id:
        return f"{user_id}_chat_{chat_id}"
    return f"{user_id}_active"

def get_user_data(user_id: str, chat_id: Optional[int] = None):
    """Obtiene los datos del usuario asegurando siempre un formato de diccionario."""
    session_key = get_session_key(user_id, chat_id)
    
    # 1. Intentar desde memoria
    if session_key in data_store:
        data = data_store[session_key]
        if data is not None:
            if isinstance(data, pd.DataFrame):
                data = {"type": "file", "data": {"dataset_1": data}, "sources": []}
                data_store[session_key] = data
            return data
    
    # 2. Intentar desde archivo (persistencia)
    try:
        session_file = get_session_file(user_id)
        if os.path.exists(session_file):
            stored_data = pd.read_pickle(session_file)
            if isinstance(stored_data, pd.DataFrame):
                stored_data = {"type": "file", "data": {"dataset_1": stored_data}, "sources": []}
            data_store[session_key] = stored_data
            return stored_data
    except Exception as e:
        logger.error(f"Error cargando sesión persistente para {user_id}: {e}")
    
    # 3. FALLBACK: Heredar de sesión activa
    if chat_id:
        active_key = get_session_key(user_id, None)
        active_data = data_store.get(active_key)
        if active_data is not None:
            data_store[session_key] = active_data
            return active_data
            
    return None

def save_user_data(user_id: str, data: dict):
    """Guarda los datos de la sesión en disco para persistencia."""
    if data is None: return
    try:
        session_file = get_session_file(user_id)
        # Usamos pickle para guardar el diccionario completo de DataFrames
        pd.to_pickle(data, session_file)
        logger.info(f"Sesión persistida en disco para {user_id}")
    except Exception as e:
        logger.error(f"Error al persistir sesión para {user_id}: {e}")

def promote_active_session(user_id: str, chat_id: int):
    """Vincula los datos de la sesión activa a un chat específico recién creado."""
    active_key = get_session_key(user_id, None)
    chat_key = get_session_key(user_id, chat_id)
    
    if active_key in data_store and data_store[active_key] is not None:
        data_store[chat_key] = data_store[active_key]
        logger.info(f"Sesión activa promocionada al chat {chat_id} para {user_id}")
        return True
    return False

def load_source_to_session(user_id: str, source, chat_id: Optional[int] = None) -> bool:
    """Carga una fuente de datos específica al contexto de memoria (Chat o Activo) de forma aditiva."""
    session_key = get_session_key(user_id, chat_id)
    try:
        # Asegurar sincronización con la nube
        if hasattr(source, 'url') and source.url:
            sync_cloud_to_local(source.url)

        # 1. Obtener sesión actual para no perder lo que ya estaba
        session_data = get_user_data(user_id, chat_id)
        if session_data is None or session_data.get("type") != source.type:
            session_data = {"type": source.type, "data": {}, "sources": []}
        
        if source.type == 'file':
            actual_url = source.url
            if os.path.exists(actual_url):
                from src.connectors.data_connectors import load_file_data
                df = load_file_data(actual_url)
                
                # Nombre seguro para la tabla
                safe_name = "".join([c if c.isalnum() else "_" for c in source.name.split('.')[0]])
                session_data["data"][safe_name] = df
                
                if source.id not in session_data["sources"]:
                    session_data["sources"].append(source.id)
                
                data_store[session_key] = session_data
                save_user_data(user_id, session_data)
                return True
        elif source.type == 'sql':
            from src.connectors.data_connectors import get_sql_engine, get_db_schema
            engine = get_sql_engine(source.url)
            schema = get_db_schema(engine)
            session_data = {"type": "sql", "data": engine, "schema": schema, "source_id": source.id}
            data_store[session_key] = session_data
            save_user_data(user_id, session_data)
            return True
        elif source.type == 'gsheets':
            from src.connectors.data_connectors import load_gsheets_data
            df = load_gsheets_data(source.url)
            if df is not None:
                sheet_key = f"gsheet_{source.id}"
                session_data["data"][sheet_key] = df
                if source.id not in session_data["sources"]:
                    session_data["sources"].append(source.id)
                data_store[session_key] = session_data
                save_user_data(user_id, session_data)
                return True
    except Exception as e:
        logger.error(f"Error en load_source_to_session ({session_key}): {e}")
    return False
