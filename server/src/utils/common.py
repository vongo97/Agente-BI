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

# Almacenamiento temporal de datos con límite de tamaño y TTL (P-35)
class _BoundedStore:
    """Diccionario con límite máximo de entradas y TTL por entrada.

    Cuando se excede max_entries, se elimina la entrada más antigua (por
    tiempo de inserción). Cuando una entrada excede ttl_seconds, se considera
    expirada y se elimina al acceder.
    """

    def __init__(self, max_entries: int = 100, ttl_seconds: int = 3600):
        self._max_entries = max_entries
        self._ttl_seconds = ttl_seconds
        self._data: dict = {}
        self._timestamps: dict = {}  # clave -> timestamp de inserción

    def __getitem__(self, key):
        self._expire_if_needed(key)
        if key not in self._data:
            raise KeyError(key)
        return self._data[key]

    def __setitem__(self, key, value):
        self._evict_if_needed()
        self._data[key] = value
        self._timestamps[key] = time.time()

    def __contains__(self, key):
        self._expire_if_needed(key)
        return key in self._data

    def __delitem__(self, key):
        self._data.pop(key, None)
        self._timestamps.pop(key, None)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def pop(self, key, default=None):
        self._expire_if_needed(key)
        self._timestamps.pop(key, None)
        return self._data.pop(key, default)

    def clear(self):
        self._data.clear()
        self._timestamps.clear()

    def keys(self):
        self._expire_all()
        return self._data.keys()

    def values(self):
        self._expire_all()
        return self._data.values()

    def items(self):
        self._expire_all()
        return self._data.items()

    def __len__(self):
        self._expire_all()
        return len(self._data)

    def _expire_if_needed(self, key):
        if key in self._timestamps:
            elapsed = time.time() - self._timestamps[key]
            if elapsed > self._ttl_seconds:
                self._data.pop(key, None)
                self._timestamps.pop(key, None)

    def _expire_all(self):
        expired = [
            k for k, ts in self._timestamps.items()
            if time.time() - ts > self._ttl_seconds
        ]
        for k in expired:
            self._data.pop(k, None)
            self._timestamps.pop(k, None)

    def _evict_if_needed(self):
        if len(self._data) >= self._max_entries:
            # Eliminar la entrada más antigua por tiempo de inserción
            oldest_key = min(self._timestamps, key=self._timestamps.get)
            self._data.pop(oldest_key, None)
            self._timestamps.pop(oldest_key, None)


# Almacenamiento temporal de datos con límite y TTL (P-35)
# max_entries=100 evita OOM en Render free (512 MB); ttl_seconds=3600 (1 h)
# libera entradas de sesiones abandonadas.
data_store = _BoundedStore(max_entries=100, ttl_seconds=3600)

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

_TEST_USER = "test_user_persistence@example.com"
_DEV_ENVIRONMENTS = {"development", "dev", "local"}


def is_development_mode() -> bool:
    """True solo si el entorno lo declara explicitamente.

    El valor por defecto es 'production' a proposito: un control de seguridad no
    puede activarse por la *ausencia* de configuracion (fail-open). Para trabajar
    en local hay que declarar ENVIRONMENT=development.
    """
    return os.getenv("ENVIRONMENT", "production").strip().lower() in _DEV_ENVIRONMENTS


def _dev_bypass_allowed(request: Optional[Request]) -> bool:
    """Permite autenticar como usuario de pruebas SOLO en desarrollo local real.

    Condiciones (todas obligatorias):
      1. ENVIRONMENT declarado explicitamente como desarrollo.
      2. No estar ejecutando en Render (RENDER=true).
      3. La peticion llega desde localhost.

    Caso especial: sin contexto de request (llamadas internas o apps de test que
    no montan el middleware) se permite solo si 1 y 2 se cumplen; en produccion
    el contexto siempre existe porque lo instala el middleware.
    """
    if os.getenv("RENDER", "false").strip().lower() == "true":
        return False
    if not is_development_mode():
        return False
    if request is None:
        return True
    return _request_is_local(request)


def get_authenticated_user() -> str:
    """Extrae y valida el Bearer token del request actual.
    Retorna el email del usuario autenticado (user_id).
    En produccion exige un token JWT valido: si falta configuracion, deniega."""
    request = request_var.get()
    allow_bypass = _dev_bypass_allowed(request)
    
    if not request:
        if not allow_bypass:
            raise HTTPException(status_code=401, detail="No se encontró contexto de petición.")
        return _TEST_USER
        
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
        
    return _TEST_USER

def check_authorization(email: str):
    request = request_var.get()
    allow_bypass = _dev_bypass_allowed(request)
    
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
                # En desarrollo local se permite omitir el token si es el usuario de pruebas
                if email.lower() == _TEST_USER:
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
    if allow_bypass and email.lower() == _TEST_USER:
        return True
    if email.lower() in authorized_list:
        return True
    logger.warning(
        "AUTH_REJECTED motivo=no_autorizado user=%s (AUTHORIZED_EMAILS contiene %d correo/s)",
        mask_email(email), len(authorized_list)
    )
    raise HTTPException(status_code=403, detail="Usuario no autorizado")

def get_session_file(user_id: str, chat_id: Optional[int] = None, source_id: Optional[int] = None):
    safe_user = hashlib.md5(user_id.encode()).hexdigest()
    if source_id:
        file_path = os.path.join(SESSIONS_DIR, f"{safe_user}_{source_id}.pkl")
    elif chat_id:
        file_path = os.path.join(SESSIONS_DIR, f"{safe_user}_chat_{chat_id}.pkl")
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
    needs_resave = False
    try:
        session_file = get_session_file(user_id, chat_id=chat_id)
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
                needs_resave = True
            if isinstance(stored_data, pd.DataFrame):
                stored_data = {"type": "file", "data": {"dataset_1": stored_data}, "sources": []}
                needs_resave = True
            # Re-persistir SOLO si hubo migración. Antes se volvía a serializar,
            # cifrar y subir la sesión completa en cada lectura desde disco:
            # con varias tablas eso duplica la RAM y bloquea el request.
            if needs_resave:
                save_user_data(user_id, stored_data, chat_id=chat_id)
            data_store[session_key] = stored_data
            return stored_data
    except Exception as e:
        logger.error("Error cargando sesión persistente para %s (chat_id=%s): %s", mask_email(user_id), chat_id, e)
    
    # 3. FALLBACK: Heredar de sesión activa
    if chat_id:
        active_key = get_session_key(user_id, None)
        active_data = data_store.get(active_key)
        if active_data is not None:
            data_store[session_key] = active_data
            return active_data
            
    return None

def save_user_data(user_id: str, data: dict, chat_id: Optional[int] = None):
    """Guarda los datos de la sesión en disco (cifrada) y en la nube."""
    if data is None: return
    try:
        import pickle
        from src.utils.security import cipher_suite
        session_file = get_session_file(user_id, chat_id=chat_id)
        # Serializar y cifrar antes de escribir a disco
        raw = pickle.dumps(data)
        encrypted = cipher_suite.encrypt(raw)
        with open(session_file, 'wb') as f:
            f.write(encrypted)
        logger.info("Sesión cifrada y persistida en disco para %s (chat_id=%s)", mask_email(user_id), chat_id)
        
        # Sincronización en la Nube
        try:
            remote_path = f"sessions/{os.path.basename(session_file)}"
            upload_file_to_cloud(session_file, remote_path)
            logger.info("Sesión persistida en la nube para %s (chat_id=%s)", mask_email(user_id), chat_id)
        except Exception as upload_err:
            logger.error("Error al subir sesión a la nube para %s (chat_id=%s): %s", mask_email(user_id), chat_id, upload_err)
            
    except Exception as e:
        logger.error("Error al persistir sesión para %s (chat_id=%s): %s", mask_email(user_id), chat_id, e)

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


def load_source_to_session(
    user_id: str, source, chat_id: Optional[int] = None, persist: bool = True
) -> bool:
    """Carga una fuente de datos específica al contexto de memoria (Chat o Activo) de forma aditiva.

    ``persist=False`` evita re-serializar y re-subir la sesión completa en cada
    fuente. ``ensure_user_session`` lo usa para reconstruir el pool tras un
    reinicio y guarda una sola vez al final.
    """
    session_key = get_session_key(user_id, chat_id)
    try:
        # 1. Obtener sesión actual para no perder lo que ya estaba
        session_data = get_user_data(user_id, chat_id)
        if session_data is None or session_data.get("type") != source.type:
            session_data = {"type": source.type, "data": {}, "sources": []}
        
        if source.type == 'file':
            safe_name = "".join([c if c.isalnum() else "_" for c in source.name.split('.')[0]])
            # Si ya está cargada, no volver a descargar, descifrar y parsear.
            if source.id in session_data.get("sources", []) and safe_name in session_data.get("data", {}):
                return True
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
                session_data["data"][safe_name] = df
                
                if source.id not in session_data["sources"]:
                    session_data["sources"].append(source.id)
                
                data_store[session_key] = session_data
                if persist:
                    save_user_data(user_id, session_data, chat_id=chat_id)
                return True
        elif source.type == 'sql':
            from src.connectors.data_connectors import get_sql_engine, get_db_schema
            from src.utils.security import decrypt_key
            engine = get_sql_engine(decrypt_key(source.url) or source.url)
            schema = get_db_schema(engine)
            session_data = {"type": "sql", "data": engine, "schema": schema, "source_id": source.id}
            data_store[session_key] = session_data
            if persist:
                save_user_data(user_id, session_data, chat_id=chat_id)
            return True
        elif source.type == 'gsheets':
            sheet_key = f"gsheet_{source.id}"
            if source.id in session_data.get("sources", []) and sheet_key in session_data.get("data", {}):
                return True
            from src.connectors.data_connectors import load_gsheets_data
            df = load_gsheets_data(source.url)
            if df is not None:
                session_data["data"][sheet_key] = df
                if source.id not in session_data["sources"]:
                    session_data["sources"].append(source.id)
                data_store[session_key] = session_data
                if persist:
                    save_user_data(user_id, session_data, chat_id=chat_id)
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
    loaded_any = False
    for source in sources:
        if source.type in ("file", "gsheets"):
            # No persistir por cada fuente: con varias tablas, cada guardado
            # vuelve a serializar/cifrar/subir todo el pool y dispara la RAM.
            if load_source_to_session(user_id, source, chat_id, persist=False):
                loaded_any = True
        # type == "sql" no se reconstruye automáticamente: crear engines para
        # todas las conexiones en cada arranque sería costoso y puede fallar
        # si la URL cifrada ya no es válida. El usuario puede reconectar.

    rebuilt = get_user_data(user_id, chat_id)
    if loaded_any and rebuilt:
        save_user_data(user_id, rebuilt, chat_id=chat_id)
    return rebuilt
