import logging
import json
import re
import os
import datetime
import sys
import uuid
from contextvars import ContextVar
from typing import Any, Optional

# ──────────────────────────────────────────────────────────────────────────────
# FILTRO DE SECRETOS CENTRALIZADO
# Sanitiza TODOS los mensajes de log antes de escribirlos, sin excepción.
# Añadir aquí nuevos patrones a medida que surjan.
# ──────────────────────────────────────────────────────────────────────────────
_SECRET_PATTERNS = [
    # Passwords en connection strings:  postgresql://user:PASSWORD@host
    (re.compile(r'(\w+://[^:/]+:)(.+)(@[^@\s/:]+(?::\d+)?(?:/[^\s]*)?)', re.IGNORECASE), r'\1***\3'),
    # Bearer / Authorization tokens
    (re.compile(r'(Bearer\s+)[A-Za-z0-9\-_\.]+', re.IGNORECASE), r'\1***'),
    # API Keys genéricas: AIza..., sk-..., gAAAA...
    (re.compile(r'\b(AIza|sk-|gAAAA)[A-Za-z0-9\-_\.]{6,}\b'), r'\1***'),
    # Patrones key=VALUE en query strings o logs
    (re.compile(r'((?:api_key|token|secret|password|passwd|pwd)=)[^&\s\'"]+',
                re.IGNORECASE), r'\1***'),
    # AWS / GCP style keys (26-40 chars mayúsculas+dígitos)
    (re.compile(r'\b[A-Z0-9]{20,40}\b'), lambda m: m.group(0) if len(m.group(0)) < 24 else '***'),
]

def _sanitize_message(msg: str) -> str:
    """Aplica todos los patrones de redacción sobre un mensaje de log."""
    for pattern, repl in _SECRET_PATTERNS:
        msg = pattern.sub(repl, msg)
    return msg


class SecretFilter(logging.Filter):
    """
    Filtro de logging que enmascara secretos en el campo 'message' y en
    el traceback de cada LogRecord antes de que llegue a cualquier Handler.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        # Sanitizar el mensaje principal
        record.msg = _sanitize_message(str(record.msg))
        # Si hay args (interpolación), convertir a string ya formateado y sanitizar
        if record.args:
            try:
                record.msg = _sanitize_message(record.msg % record.args)
            except Exception as exc:
                # P-36: la interpolación puede fallar (args con formato incompatible).
                # No se puede tragar: si el mensaje queda sin formatear puede arrastrar
                # secretos sin sanear, así que se registra y se degrada a texto plano.
                log_ignored_error(
                    logging.getLogger(__name__),
                    "interpolación de un LogRecord",
                    exc,
                    level=logging.WARNING,
                    record=record.name,
                )
                record.msg = _sanitize_message(str(record.msg))
            record.args = None
        # Sanitizar traceback si existe
        if record.exc_text:
            record.exc_text = _sanitize_message(record.exc_text)
        return True  # Siempre dejar pasar el registro (solo filtra contenido)


class StructuredFormatter(logging.Formatter):
    """
    Formateador de logs que produce una salida estructurada (JSON) para producción
    y una salida legible para desarrollo.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.datetime.now().isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "lineno": record.lineno
        }
        
        # Añadir datos extra si existen
        if hasattr(record, "extra_data"):
            log_obj["extra"] = record.extra_data
            
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_obj)


def setup_logging():
    """
    Configura el sistema de logs global del servidor con filtro de secretos.
    El SecretFilter se instala en 3 capas para cobertura total:
      1. root_logger (captura la mayoría)
      2. Cada handler individual (cubre loggers hijos con propagate=False)
    """
    root_logger = logging.getLogger()
    
    # Evitar duplicados si se llama varias veces
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.setLevel(logging.INFO)

    # ── Capa 1: Filtro en el root_logger ────────────────────────────────────
    secret_filter = SecretFilter()
    root_logger.addFilter(secret_filter)

    # Handler para Consola (Legible)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
    ))
    # ── Capa 2: Filtro también en cada handler (defensa en profundidad) ──────
    console_handler.addFilter(secret_filter)
    root_logger.addHandler(console_handler)

    # Handler para Archivo (JSON Estructurado) — solo en producción para evitar ruido
    is_render = os.getenv("RENDER", "false").lower() == "true"
    if is_render:
        file_handler = logging.FileHandler("server_structured.log")
        file_handler.setFormatter(StructuredFormatter())
        file_handler.addFilter(secret_filter)   # Capa 2 también en archivo
        root_logger.addHandler(file_handler)

    # Silenciar logs ruidosos de librerías
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logging.info("Sistema de logs estructurados con filtro de secretos inicializado.")


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS DE SEGURIDAD PARA LOGGING
# ──────────────────────────────────────────────────────────────────────────────

def safe_error_message(exc: Exception) -> str:
    """
    Devuelve un mensaje de error seguro que nunca contiene datos sensibles.
    Sólo expone el tipo de la excepción, nunca su mensaje completo.
    Usar en todos los `except Exception as e` en lugar de str(e).

    Ejemplo::

        logger.error("Error en operación: %s", safe_error_message(e))
    """
    return _sanitize_message(type(exc).__name__)


# ──────────────────────────────────────────────────────────────────────────────
# REQUEST ID (P-36)
# Identificador de correlación para poder unir un log del servidor con la
# petición que lo provocó. `main.py` lo inyecta en la cabecera `X-Request-Id`
# (que ya estaba declarada en CORS pero nunca se generaba) y lo publica aquí
# para que cualquier capa pueda adjuntarlo a sus logs.
# ──────────────────────────────────────────────────────────────────────────────
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_request_id() -> str:
    """Devuelve el `X-Request-Id` de la petición en curso o '-' si no hay contexto."""
    return request_id_var.get() or "-"


def new_request_id() -> str:
    """Genera un identificador de correlación para una petición nueva."""
    return uuid.uuid4().hex


def log_ignored_error(
    logger: logging.Logger,
    context: str,
    exc: Exception,
    level: int = logging.WARNING,
    **extra_fields: Any,
) -> None:
    """Registra una excepción que se va a ignorar.

    P-36 (regla 8 del registro): *«Sin `except: pass`. Si se ignora un error, se
    registra con contexto.»* Este helper es la única forma admitida de tragarse
    una excepción: deja rastro con **tipo + mensaje saneado + request_id**.

    `context` describe la operación que falló (qué se estaba haciendo), nunca
    datos del usuario. Los campos extra se anexan al mensaje.

    Ejemplo::

        except Exception as e:
            log_ignored_error(logger, "borrado de archivo de caché", e)
    """
    fields = "".join(f" {k}={v!r}" for k, v in extra_fields.items())
    logger.log(
        level,
        "EXCEPCIÓN IGNORADA [%s] %s: %s (%s)%s",
        get_request_id(),
        context,
        type(exc).__name__,
        _sanitize_message(str(exc))[:200],
        fields,
    )


def hash_user(user_id: str) -> str:
    """
    Devuelve un hash corto del user_id para usarlo en logs de observabilidad
    sin exponer el email completo.

    Ejemplo::

        logger.info("analysis_started", extra={"extra_data": {"user_hash": hash_user(user)}})
    """
    import hashlib
    return hashlib.sha256(user_id.encode()).hexdigest()[:12]

