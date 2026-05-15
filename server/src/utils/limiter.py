from slowapi import Limiter
from slowapi.util import get_remote_address

# Instancia global del limitador para evitar importaciones circulares entre main y routers
limiter = Limiter(key_func=get_remote_address)
