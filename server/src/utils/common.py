import os
import pandas as pd
import hashlib
import logging
from typing import Optional
from fastapi import HTTPException, Request
from src.utils.supabase_storage import sync_cloud_to_local, upload_file_to_cloud
from src.services.storage_service import download_bytes, is_cloud_key
from contextvars import ContextVar
import hmac
import base64
import time
import jwt

# Configuración de Logs
logger = logging.getLogger(__name__)

# Almacenamiento temporal de datos
data_store = {}

# ContextVar para almacenar el request actual de forma segura para hilos/corutinas
request_var: ContextVar[Optional[Request]] = ContextVar("request", default=None)

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

def mask_email(email: Optional[str]) -> str:
    """Enmascara un email para logs: 'usuario@dominio.com' → 'u***@dominio.com'."""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return f"{local[:1]}***@{domain}"

# Directorios de Almacenamiento (Persistencia en Render)
STORAGE_ROOT = "/data" if os.path.exists("/data") else "."
SESSIONS_DIR = os.path.join(STORAGE_ROOT, "sessions_cache")
DATA_SOURCES_DIR = os.path.join(STORAGE_ROOT, "data_sources")

for d in [SESSIONS_DIR, DATA_SOURCES_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

def verify_token(token: str, secret: str) -> Optional[dict]:
    """Valida la firma HMAC-SHA256 y la expiración del token JWT utilizando PyJWT estándar."""
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expirado.")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token inválido: {e}")
        return None

def _request_is_local(request: Request) -> bool:
    """Determina si la petición proviene de una interfaz local (desarrollo en máquina local)."""
    try:
        client_host = request.client.host if request.client else None
        url_host = (request.url.hostname or "").lower()
        return client_host in ("127.0.0.1", "::1", "localhost") or url_host in ("localhost", "127.0.0.1", "::1")
    except Exception:
        return False

def _resolve_auth_secret(request: Optional[Request], allow_bypass: bool) -> str:
    """Resuelve el secreto para verificar JWT.
    El fallback de desarrollo solo se permite si la petición es estrictamente local
    (evita que un entorno 'development' público en un VPS quede falsificable)."""
    secret = os.getenv("AUTH_SECRET") or os.getenv("NEXTAUTH_SECRET")
    if secret:
        return secret
    if not allow_bypass or not (request and _request_is_local(request)):
        raise HTTPException(
            status_code=500,
            detail="Error de configuracion de seguridad: falta definir AUTH_SECRET o NEXTAUTH_SECRET en produccion."
        )
    logger.warning("USANDO SECRETO DE DESARROLLO POR DEFECTO - solo válido en localhost. Define AUTH_SECRET.")
    return "secreto-desarrollo-por-defecto"

def get_authenticated_user() -> str:
    """Extrae y valida el Bearer token del request actual.
    Retorna el email del usuario autenticado (user_id).
    En producción, exige un token JWT estándar válido.
    En desarrollo local, si no hay token, retorna el test_user por defecto."""
    request = request_var.get()
    is_render = os.getenv("RENDER", "false").lower() == "true"
    is_dev = os.getenv("ENVIRONMENT", "development").lower() == "development"
    allow_bypass = (not is_render) and is_dev
    
    if not request:
        if not allow_bypass:
            raise HTTPException(status_code=401, detail="No se encontró contexto de petición.")
        return "test_user_persistence@example.com"
        
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        secret = _resolve_auth_secret(request, allow_bypass)
        
        payload = verify_token(token, secret)
        if not payload:
            raise HTTPException(status_code=401, detail="Token de sesión inválido o expirado.")
            
        return payload.get("user_id", "").lower()
        
    if not allow_bypass:
        raise HTTPException(status_code=401, detail="Se requiere token de autenticación (Bearer Token) en producción.")
        
    return "test_user_persistence@example.com"

def check_authorization(email: str):
    request = request_var.get()
    is_render = os.getenv("RENDER", "false").lower() == "true"
    is_dev = os.getenv("ENVIRONMENT", "development").lower() == "development"
    allow_bypass = (not is_render) and is_dev
    
    # 1. Validar Bearer Token si el request está configurado en el contexto asíncrono
    if request:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            secret = _resolve_auth_secret(request, allow_bypass)
            
            payload = verify_token(token, secret)
            if not payload:
                raise HTTPException(status_code=401, detail="Token de sesión inválido o expirado.")
            
            # El email autenticado por el token DEBE coincidir con el email de la consulta
            token_email = payload.get("user_id", "").lower()
            if token_email != email.lower():
                logger.warning(
                    "AUTH_REJECTED motivo=token_user_mismatch token_user=%s requested_user=%s",
                    mask_email(token_email), mask_email(email)
                )
                raise HTTPException(status_code=403, detail="El token de sesión no coincide con el usuario solicitado.")
        else:
            # Exigir token obligatorio en producción para todos (sin bypass para test_user)
            if not allow_bypass:
                raise HTTPException(status_code=401, detail="Se requiere token de autenticación (Bearer Token) en producción.")
            else:
                # En desarrollo local se permite omitir el token si es test_user_persistence@example.com
                if email.lower() == "test_user_persistence@example.com":
                    return True

    # 2. Comprobar contra lista de emails autorizados
    authorized_env = os.getenv("AUTHORIZED_EMAILS", "")
    
    if not authorized_env:
        if not allow_bypass:
            logger.warning(
                "AUTH_REJECTED motivo=authorized_emails_vacia user=%s "
                "(definir AUTHORIZED_EMAILS en el panel del servicio)",
                mask_email(email)
            )
            raise HTTPException(status_code=403, detail="Acceso denegado: AUTHORIZED_EMAILS no configurada en producción.")
        return True
        
    authorized_list = [e.strip().lower() for e in authorized_env.split(",") if e.strip()]
    # En producción test_user_persistence NO se exime si no está en la lista blanca
    if allow_bypass and email.lower() == "test_user_persistence@example.com":
        return True
    if email.lower() in authorized_list:
        return True
    logger.warning(
        "AUTH_REJECTED motivo=no_autorizado user=%s (AUTHORIZED_EMAILS contiene %d correo/s)",
        mask_email(email), len(authorized_list)
    )
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
            import pickle
            from src.utils.security import cipher_suite
            with open(session_file, 'rb') as f:
                raw = f.read()
            # Intentar descifrar (archivos nuevos)
            try:
                decrypted = cipher_suite.decrypt(raw)
                stored_data = pickle.loads(decrypted)
            except Exception:
                # Migración segura: solo aceptar pickle plano si claramente es un archivo
                # heredado (no empieza con token Fernet 'gAAA...') y nunca contienen
                # datos arbitrarios de terceros: los re-ciframos de inmediato.
                if raw.strip().startswith(b"gAAA"):
                    logger.error("Archivo de sesión cifrado inválido; se ignora para prevenir RCE.")
                    raise ValueError("Sesión cifrada corrupta o manipulada")
                logger.warning("Migrando sesión heredada sin cifrar (%s) a formato cifrado.", session_file)
                stored_data = pickle.loads(raw)
            if isinstance(stored_data, pd.DataFrame):
                stored_data = {"type": "file", "data": {"dataset_1": stored_data}, "sources": []}
            # Re-persistir en formato cifrado si venía de archivo plano heredado
            save_user_data(user_id, stored_data)
            data_store[session_key] = stored_data
            return stored_data
    except Exception as e:
        logger.error("Error cargando sesión persistente para %s: %s", mask_email(user_id), e)
    
    # 3. FALLBACK: Heredar de sesión activa
    if chat_id:
        active_key = get_session_key(user_id, None)
        active_data = data_store.get(active_key)
        if active_data is not None:
            data_store[session_key] = active_data
            return active_data
            
    return None

def save_user_data(user_id: str, data: dict):
    """Guarda los datos de la sesión en disco (cifrada) y en la nube."""
    if data is None: return
    try:
        import pickle
        from src.utils.security import cipher_suite
        session_file = get_session_file(user_id)
        # Serializar y cifrar antes de escribir a disco
        raw = pickle.dumps(data)
        encrypted = cipher_suite.encrypt(raw)
        with open(session_file, 'wb') as f:
            f.write(encrypted)
        logger.info("Sesión cifrada y persistida en disco para %s", mask_email(user_id))
        
        # Sincronización en la Nube
        try:
            remote_path = f"sessions/{os.path.basename(session_file)}"
            upload_file_to_cloud(session_file, remote_path)
            logger.info("Sesión persistida en la nube para %s", mask_email(user_id))
        except Exception as upload_err:
            logger.error("Error al subir sesión a la nube para %s: %s", mask_email(user_id), upload_err)
            
    except Exception as e:
        logger.error("Error al persistir sesión para %s: %s", mask_email(user_id), e)

def promote_active_session(user_id: str, chat_id: int):
    """Vincula los datos de la sesión activa a un chat específico recién creado."""
    active_key = get_session_key(user_id, None)
    chat_key = get_session_key(user_id, chat_id)
    
    if active_key in data_store and data_store[active_key] is not None:
        data_store[chat_key] = data_store[active_key]
        logger.info("Sesión activa promocionada al chat %s para %s", chat_id, mask_email(user_id))
        return True
    return False

def resolve_source_path(source) -> Optional[str]:
    """Devuelve una ruta local legible para el archivo de una DataSource.

    Orden de resolución:
    1. Ruta local existente (filas de legado pre-refactor).
    2. Clave de nube (``data_sources/...``): descarga a la caché local desde
       Supabase. La nube es la fuente de verdad; el disco es desechable.
    3. Legado sin clave: intento de derivación por basename (sync_cloud_to_local).

    None si no hay forma de obtener el archivo (nube caída, objeto borrado,
    claves de cifrado cambiadas, etc.).
    """
    url = getattr(source, 'url', None)
    if not url:
        return None

    # 1. Legado: ruta local válida en este contenedor
    if os.path.exists(url):
        return url

    # 2. Clave de nube explícita (formato nuevo)
    if is_cloud_key(url):
        data = download_bytes(url)
        if data:
            try:
                os.makedirs(DATA_SOURCES_DIR, exist_ok=True)
                local_path = os.path.join(DATA_SOURCES_DIR, os.path.basename(url.replace("\\", "/")))
                with open(local_path, 'wb') as f:
                    f.write(data)
                return local_path
            except Exception as e:
                logger.error("No se pudo cachear '%s' en disco: %s", mask_email(str(source.name)), e)
        else:
            logger.warning(
                "Archivo no recuperable desde la nube (key=%s). Posibles causas: "
                "bucket no configurado, objeto borrado o ENCRYPTION_KEY cambiada.",
                url.replace("\\", "/").split("/")[-1],
            )
        return None

    # 3. Legado: derivar clave desde basename y sincronizar
    if sync_cloud_to_local(url) and os.path.exists(url):
        return url
    return None


def load_source_to_session(user_id: str, source, chat_id: Optional[int] = None) -> bool:
    """Carga una fuente de datos específica al contexto de memoria (Chat o Activo) de forma aditiva."""
    session_key = get_session_key(user_id, chat_id)
    try:
        # 1. Obtener sesión actual para no perder lo que ya estaba
        session_data = get_user_data(user_id, chat_id)
        if session_data is None or session_data.get("type") != source.type:
            session_data = {"type": source.type, "data": {}, "sources": []}
        
        if source.type == 'file':
            # La nube es la fuente de verdad: resuelve la clave de bucket y
            # descarga a la caché local si el archivo no está en el contenedor.
            local_path = resolve_source_path(source)
            if local_path:
                is_encrypted = getattr(source, 'is_encrypted', False)
                if is_encrypted:
                    # Descifrar en memoria, nunca en disco
                    from src.utils.security import decrypt_file_to_bytes
                    from src.connectors.data_connectors import load_file_data_from_bytes
                    try:
                        raw_bytes = decrypt_file_to_bytes(local_path)
                        df = load_file_data_from_bytes(raw_bytes, source.name)
                    except Exception as dec_err:
                        logger.error("Error descifrando archivo %s: %s", local_path, dec_err)
                        return False
                else:
                    # Fallback: archivos anteriores sin cifrar
                    from src.connectors.data_connectors import load_file_data
                    df = load_file_data(local_path)
                
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
            from src.utils.security import decrypt_key
            engine = get_sql_engine(decrypt_key(source.url) or source.url)
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


def ensure_user_session(user_id: str, db, chat_id: Optional[int] = None):
    """Garantiza una sesión con datos, reconstruyéndola tras un reinicio.

    Si la caché en memoria y el pickle local están vacíos (contenedor recién
    levantado), reconstruye el pool desde la base de datos descargando cada
    fuente de tipo archivo desde la nube. Es el mecanismo que hace que el
    usuario NO tenga que volver a subir sus documentos tras un deploy.

    Devuelve session_data o None si no hay fuentes recuperables.
    """
    session_data = get_user_data(user_id, chat_id)
    if session_data and session_data.get("data"):
        return session_data

    from src.database import DataSource  # import local: evita ciclo de imports
    sources = db.query(DataSource).filter(DataSource.user_id == user_id).all()
    if not sources:
        return session_data  # None o vacío: no hay nada registrado para este usuario

    logger.info(
        "Reconstruyendo sesión desde DB+nube para %s (%d fuente(s)).",
        mask_email(user_id), len(sources),
    )
    for source in sources:
        if source.type in ("file", "gsheets"):
            load_source_to_session(user_id, source, chat_id)
        # type == "sql" no se reconstruye automáticamente: crear engines para
        # todas las conexiones en cada arranque sería costoso y puede fallar
        # si la URL cifrada ya no es válida. El usuario puede reconectar.

    return get_user_data(user_id, chat_id)
