import logging

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

logger = logging.getLogger(__name__)


def get_user_or_ip(request: Request) -> str:
    """
    Key function para el rate limiter.

    Prioriza el usuario autenticado (email del JWT) sobre la IP, evitando que
    usuarios en NAT compartida se bloqueen mutuamente. Si no hay token válido,
    cae a la IP del par TCP.

    Nota de seguridad (P-31): se usa `get_remote_address`, que lee
    `request.client.host` y **no** `X-Forwarded-For`. Uvicorn solo confía en la
    cabecera cuando el par está en `FORWARDED_ALLOW_IPS` (por defecto 127.0.0.1),
    así que un cliente no puede evadir el límite falsificando la cabecera. El
    efecto secundario es que, detrás del proxy de Render, las peticiones
    anónimas comparten el cubo de la IP del proxy; los endpoints autenticados
    no se ven afectados porque se agrupan por usuario.
    """
    try:
        from src.utils.common import get_authenticated_user
        user = get_authenticated_user()
        if user:
            return user
    except Exception as exc:  # sin contexto de request o token inválido
        logger.debug("Rate limit: sin identidad de usuario (%s); se usa la IP.", type(exc).__name__)
    return get_remote_address(request)


# Instancia global del limitador
limiter = Limiter(key_func=get_user_or_ip)
