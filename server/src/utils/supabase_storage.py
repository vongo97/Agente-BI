import os
import logging

# Capa de compatibilidad: la lógica real vive en src.services.storage_service.
# Los módulos legacy (common.py, simulation.py) siguen importando de aquí.
from src.services.storage_service import (  # noqa: F401
    BUCKET_NAME,
    CLOUD_KEY_PREFIXES,
    delete_object,
    download_bytes,
    get_supabase_client,
    is_cloud_key,
    probe_bucket,
    storage_configured,
    upload_bytes,
)

logger = logging.getLogger(__name__)


def storage_diagnostic() -> dict:
    """Información segura del almacenamiento (nunca incluye URLs ni credenciales).

    `cloud` refleja que las credenciales existen; `connected` es una comprobación
    real contra el bucket (con cache de 60 s) para que /health no reporte un
    falso "cloud:true" cuando el bucket no existe o el proyecto es incorrecto.
    """
    configured = storage_configured()
    if not configured:
        logger.warning(
            "CONFIG: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY no configuradas. "
            "Los archivos y sesiones se guardan solo en el disco local, que en Render "
            "se pierde en cada reinicio. Define ambas variables en el panel del servicio."
        )
        return {"cloud": False, "connected": False, "bucket": None, "reason": "not_configured"}

    probe = probe_bucket()
    return {
        "cloud": True,
        "connected": probe["ok"],
        "bucket": BUCKET_NAME,
        "reason": probe["reason"],
    }


def upload_file_to_cloud(local_path: str, remote_path: str):
    """Sube un archivo local al bucket. Devuelve False si la nube no está
    disponible (el llamador debe avisar al usuario, no fallar en silencio)."""
    if not storage_configured():
        logger.critical(
            "SIN PERSISTENCIA EN NUBE: no se puede subir '%s' a Supabase "
            "(revisa SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY). El archivo solo "
            "vivirá en el disco local y se perderá en el próximo reinicio.", remote_path
        )
        return False
    try:
        with open(local_path, 'rb') as f:
            return upload_bytes(remote_path, f.read())
    except Exception as e:
        logger.critical(
            "FALLO al subir '%s' al bucket '%s' en Supabase: %s. Si el error menciona "
            "'bucket not found', crea el bucket '%s' (privado) en el panel de Supabase. "
            "El archivo queda solo en disco local.",
            remote_path, BUCKET_NAME, type(e).__name__, BUCKET_NAME
        )
        return False


def download_file_from_cloud(remote_path: str, local_path: str):
    """Descarga un objeto de Supabase a una ruta local."""
    data = download_bytes(remote_path)
    if data is None:
        return False
    try:
        os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
        with open(local_path, 'wb') as f:
            f.write(data)
        return True
    except Exception as e:
        logger.warning("No se pudo escribir '%s' en disco: %s", local_path, type(e).__name__)
        return False


def sync_cloud_to_local(local_path: str, remote_key: str = None):
    """Si el archivo no existe localmente, lo trae de la nube.

    `remote_key` permite pasar la clave explícita del bucket (recomendado desde
    que DataSource.url guarda claves de nube). Sin ella, se deriva del basename
    para compatibilidad con filas de legado.
    """
    if os.path.exists(local_path):
        return True

    if remote_key:
        return download_file_from_cloud(remote_key, local_path)

    # Legado: derivar la clave a partir del basename del path local
    remote_path = local_path.replace("\\", "/").split("/")[-1]
    if "sessions_cache" in local_path:
        remote_path = f"sessions/{remote_path}"
    elif "data_sources" in local_path:
        remote_path = f"data_sources/{remote_path}"

    return download_file_from_cloud(remote_path, local_path)
