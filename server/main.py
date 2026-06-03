import uvicorn
import logging
import os
import warnings
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Silenciar advertencias de formato de fecha
warnings.filterwarnings("ignore", category=UserWarning)
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Cargar variables de entorno lo antes posible
load_dotenv()

# Importar routers, utilidades y rate limiting
from src.database import init_db
from src.utils.limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

app = FastAPI(title="Vektra BI API (Modular)")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from src.routers import auth, data, analysis, dashboard, exports, simulation, visual_summary
from src.utils.common import request_var

# Configuración de Logs Estructurados
from src.utils.logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

# Configurar CORS
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "https://agente-bi.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Middleware: Security Headers ──────────────────────────────────────────────
@app.middleware("http")
async def security_headers_middleware(request, call_next):
    """Inyecta headers de seguridad en todas las respuestas HTTP."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

# ── Middleware: Request Context (JWT / auth) ──────────────────────────────────
@app.middleware("http")
async def set_request_context_middleware(request, call_next):
    token = request_var.set(request)
    try:
        return await call_next(request)
    finally:
        request_var.reset(token)

# ── Middleware: Global 500 handler ────────────────────────────────────────────
@app.middleware("http")
async def catch_exceptions_middleware(request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        is_render = os.environ.get("RENDER", "false").lower() == "true"

        if is_render:
            # Producción: solo tipo de error, sin tracebacks ni str(e)
            logger.error("GLOBAL 500 ERROR [%s]", type(e).__name__)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal Server Error. Por favor contacta al administrador."}
            )
        else:
            # Desarrollo: traceback completo al logger (pasa por SecretFilter)
            logger.exception("GLOBAL 500 ERROR [%s]", type(e).__name__)
            return JSONResponse(
                status_code=500,
                content={"detail": f"Internal Server Error: {type(e).__name__}"}
            )

# Registrar Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(data.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(exports.router, prefix="/api/v1")
app.include_router(simulation.router, prefix="/api/v1")
app.include_router(visual_summary.router, prefix="/api/v1")

# Inicializar Base de Datos
init_db()

@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "Agente BI API is running (Modular Mode)",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    is_render = os.environ.get("RENDER", "false").lower() == "true"
    reload_enabled = not is_render

    logger.info(
        "Iniciando servidor en modo %s (reload=%s, port=%d)",
        "PRODUCTION" if is_render else "DEVELOPMENT",
        reload_enabled,
        port
    )
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload_enabled)


