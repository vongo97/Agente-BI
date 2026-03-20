import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Configuración desde variables de entorno
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
BUCKET_NAME = "bi_storage"

# Inicializar cliente de forma perezosa (Lazy)
def get_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        logger.error(f"Error inicializando cliente Supabase: {e}")
        return None

def upload_file_to_cloud(local_path: str, remote_path: str):
    """Sube un archivo local al Bucket de Supabase."""
    client = get_supabase_client()
    if not client:
        logger.warning(f"No se pudo subir {remote_path}: Cliente no inicializado (revisa .env)")
        return False
    
    try:
        with open(local_path, 'rb') as f:
            response = client.storage.from_(BUCKET_NAME).upload(
                path=remote_path,
                file=f,
                file_options={"x-upsert": "true"}
            )
        return True
    except Exception as e:
        logger.error(f"Error subiendo archivo a Supabase ({remote_path}): {e}")
        return False

def download_file_from_cloud(remote_path: str, local_path: str):
    """Descarga un archivo de Supabase al sistema local."""
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        # Crear directorio local si no existe
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        response = client.storage.from_(BUCKET_NAME).download(remote_path)
        with open(local_path, 'wb') as f:
            f.write(response)
        return True
    except Exception as e:
        # No logueamos error aquí si el archivo simplemente no existe (es un fallback)
        return False

def sync_cloud_to_local(local_path: str):
    """
    Si el archivo no existe localmente, intenta traerlo de la nube.
    Útil para persistencia en Render tras reinicios.
    """
    if os.path.exists(local_path):
        return True
    
    # El remote_path será relativo a la raíz del bucket
    # Convertimos rutas absolutas de Windows/Linux a una ruta de bucket limpia
    remote_path = local_path.replace("\\", "/").split("/")[-1]
    
    # Intentamos buscarlo en subcarpetas del bucket si es necesario
    # Por ahora, usamos solo el nombre del archivo para simplicidad del MVP
    if "sessions_cache" in local_path:
        remote_path = f"sessions/{remote_path}"
    elif "data_sources" in local_path:
        remote_path = f"sources/{remote_path}"
        
    return download_file_from_cloud(remote_path, local_path)
