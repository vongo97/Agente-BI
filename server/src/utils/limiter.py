from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def get_user_or_ip(request: Request) -> str:
    """
    Key function para el rate limiter.
    Prioriza el usuario autenticado (email del JWT) sobre la IP,
    evitando que usuarios en NAT compartida se bloqueen mutuamente.
    Fallback seguro a IP si no hay token válido.
    """
    try:
        from src.utils.common import get_authenticated_user
        user = get_authenticated_user()
        if user:
            return user
    except Exception:
        pass
    return get_remote_address(request)


# Instancia global del limitador
limiter = Limiter(key_func=get_user_or_ip)
