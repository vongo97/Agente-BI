"""Fachada única sobre Supabase Storage (bucket `bi_storage`).

Contrato de la refactorización de persistencia (2026-10):

- La NUBE es la fuente de verdad de los archivos del usuario.
- El disco del contenedor (Render) es una caché desechable: nunca se confía
  en él para recuperar datos tras un reinicio.
- Toda `key` es RELATIVA A LA RAÍZ DEL BUCKET (p. ej.
  ``data_sources/ab12f3.../archivo.csv``).
- ``DataSource.url`` guarda la clave de nube. Las rutas locales absolutas solo
  existen en filas de legado (pre-refactor) y se resuelven con compatibilidad
  hacia atrás desde ``src.utils.common.resolve_source_path``.
"""
import os
import logging
from typing import Optional

from supabase import create_client

logger = logging.getLogger(__name__)

BUCKET_NAME = "bi_storage"

# Claves de bucket gestionadas por la aplicación. Cualquier `DataSource.url`
# que empiece por uno de estos prefijos es una clave de nube, no una ruta local.
CLOUD_KEY_PREFIXES = ("data_sources/", "sessions/")


def storage_configured() -> bool:
    """True si hay credenciales de Supabase (no valida que el bucket exista)."""
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


# Motivos estables y sin secretos que /health puede publicar. Los mensajes de
# supabase-py para el fallo de init son estáticos ("Invalid URL", "... is
# required"); nunca contienen la credencial. Aun así no reenviamos texto libre.
_CLIENT_INIT_REASONS = (
    ("supabase_url is required", "not_configured"),
    ("supabase_key is required", "not_configured"),
    ("invalid url", "invalid_url"),
    ("invalid api key", "invalid_api_key"),
)

# Último motivo del fallo de init, para que probe_bucket pueda reportarlo.
_last_client_error: Optional[str] = None


def _client_init_reason(exc: Exception) -> str:
    """Traduce el error de ``create_client`` a un motivo estable y sin secretos."""
    detail = str(exc).strip().lower()
    for fragment, reason in _CLIENT_INIT_REASONS:
        if fragment in detail:
            return reason
    return "client_init_failed"


def get_supabase_client():
    """Cliente Supabase perezoso. None si no hay configuración o falla el init."""
    global _last_client_error
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        _last_client_error = None
        return None
    try:
        client = create_client(url, key)
        _last_client_error = None
        return client
    except Exception as e:
        _last_client_error = _client_init_reason(e)
        logger.error(
            "Error inicializando cliente Supabase (%s). Revisa SUPABASE_URL "
            "(debe ser https://<proyecto>.supabase.co) y "
            "SUPABASE_SERVICE_ROLE_KEY.",
            _last_client_error,
        )
        return None


def is_cloud_key(value: Optional[str]) -> bool:
    """True si `value` es una clave de bucket (no una ruta local del contenedor).

    Las filas de legado guardan rutas absolutas o relativas al proceso
    ("C:/.../data_sources/x", "/data/data_sources/x"); las nuevas guardan
    claves "data_sources/...". El prefijo desambigua sin ambigüedad.
    """
    if not value:
        return False
    return value.replace("\\", "/").startswith(CLOUD_KEY_PREFIXES)


# Cache corto del probe: /health es sondeado cada ~30 s por Render y no
# queremos un listado contra Supabase en cada ping.
_probe_cache: dict = {"ok": None, "reason": None, "ts": 0.0}
_PROBE_TTL_SECONDS = 60.0


def probe_bucket(force: bool = False) -> dict:
    """Comprobación REAL de la nube: lista el bucket (límite 1).

    Devuelve {"ok": bool, "reason": str|None}. A diferencia de
    ``storage_configured`` (solo mira env vars), esto detecta bucket inexistente,
    claves inválidas o proyecto equivocado — las causas reales de la
    "persistencia degradada" que antes se reportaban como cloud:true.
    """
    import time

    now = time.time()
    if (
        not force
        and _probe_cache["ok"] is not None
        and now - _probe_cache["ts"] < _PROBE_TTL_SECONDS
    ):
        return {"ok": _probe_cache["ok"], "reason": _probe_cache["reason"]}

    client = get_supabase_client()
    if not client:
        if not storage_configured():
            reason = "not_configured"
        else:
            # Hay credenciales pero el cliente no se pudo crear: URL con typo,
            # etc. Antes se reportaba "not_configured" y ocultaba la causa real.
            reason = _last_client_error or "client_init_failed"
        result = {"ok": False, "reason": reason}
    else:
        try:
            client.storage.from_(BUCKET_NAME).list(path="", options={"limit": 1})
            result = {"ok": True, "reason": None}
        except Exception as e:
            reason = type(e).__name__
            logger.warning(
                "PROBE bucket '%s' falló (%s). Si el motivo es 'bucket not found', "
                "crea el bucket privado '%s' en Supabase o revisa SUPABASE_URL "
                "(¿apunta al proyecto correcto?).",
                BUCKET_NAME, reason, BUCKET_NAME,
            )
            result = {"ok": False, "reason": reason}

    _probe_cache.update(ok=result["ok"], reason=result["reason"], ts=now)
    return result


def upload_bytes(key: str, data: bytes) -> bool:
    """Sube bytes a la clave `key` del bucket (upsert). False si la nube no
    está disponible — el llamador DEBE tratarlo como error, no como aviso."""
    client = get_supabase_client()
    if not client:
        logger.error(
            "STORAGE_UPLOAD_ABORTED motivo=%s key=%s "
            "(SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY ausentes o inválidas).",
            _last_client_error or "not_configured", key,
        )
        return False
    try:
        client.storage.from_(BUCKET_NAME).upload(
            path=key,
            file=data,
            file_options={"x-upsert": "true"},
        )
        return True
    except Exception as e:
        logger.error(
            "STORAGE_UPLOAD_FAILED key=%s bucket=%s error=%s", key, BUCKET_NAME, type(e).__name__,
        )
        return False


def download_bytes(key: str) -> Optional[bytes]:
    """Descarga el objeto en `key`. None si no existe o la nube no responde."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        return client.storage.from_(BUCKET_NAME).download(key)
    except Exception:
        # No loguear como error: la ausencia del objeto es un fallback esperado.
        return None


def delete_object(key: str) -> bool:
    """Elimina el objeto en `key`. False si la nube no responde."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        client.storage.from_(BUCKET_NAME).remove([key])
        return True
    except Exception as e:
        logger.warning("STORAGE_DELETE_FAILED key=%s error=%s", key, type(e).__name__)
        return False
