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
from src.utils.common import request_var, is_development_mode

# Configuración de Logs Estructurados
from src.utils.logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

# Configurar CORS restringido solo a dominios de producción
# Se lee de la variable de entorno ALLOWED_ORIGINS (separada por comas) para
# poder cambiar de dominio del frontend sin tocar código. Si no está definida,
# se usa el dominio histórico por defecto.
_allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "").strip()
if _allowed_origins_env:
    ALLOWED_ORIGINS = [o.strip() for o in _allowed_origins_env.split(",") if o.strip()]
else:
    ALLOWED_ORIGINS = [
        "https://agente-bi.vercel.app",
        "https://agente-bi.onrender.com",
        "https://agente-bi-client-5nx4.onrender.com",
        "https://agente-bi-client.onrender.com",
        "https://vektra-bi-eight.vercel.app",
        # Agregar dominios corporativos específicos aquí en producción
        # Ej: "https://app.ejemplo.com", "https://admin.ejemplo.com"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Disposition", "X-Request-Id"],
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

# ── Auditoría de configuración de autorización ───────────────────────────────
# Si AUTHORIZED_EMAILS no está definida, TODOS los endpoints protegidos
# responden 403 y el navegador muestra un error genérico. Se avisa al arrancar.
_authorized_env = os.getenv("AUTHORIZED_EMAILS", "").strip()
_authorized_list = [e.strip() for e in _authorized_env.split(",") if e.strip()]
if not _authorized_list:
    logger.warning(
        "CONFIG: AUTHORIZED_EMAILS vacía o ausente -> todos los endpoints "
        "protegidos responderán 403 'Acceso denegado'. Defínela en el panel del servicio."
    )
else:
    logger.info("CONFIG: %d correo(s) en la lista blanca AUTHORIZED_EMAILS", len(_authorized_list))

# ── Auditoría del modo de autenticación ──────────────────────────────────────
# El bypass de token (usuario de pruebas) solo existe en desarrollo local real.
# Si el entorno no declara ENVIRONMENT, el modo por defecto es produccion.
if is_development_mode() and os.getenv("RENDER", "false").strip().lower() != "true":
    logger.warning(
        "CONFIG: MODO DESARROLLO (ENVIRONMENT=%s) -> usuario de pruebas sin token "
        "permitido SOLO desde localhost. En produccion define ENVIRONMENT=production.",
        os.getenv("ENVIRONMENT", "production"),
    )

# Registrar Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(data.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(exports.router, prefix="/api/v1")
app.include_router(simulation.router, prefix="/api/v1")
app.include_router(visual_summary.router, prefix="/api/v1")

# Inicializar Base de Datos de forma segura
try:
    init_db()
except Exception as e:
    logger.error("No se pudo completar init_db al iniciar: %s", e)

@app.get("/live")
async def live():
    """Health check ligero para Render: no toca DB ni almacenamiento."""
    return {"status": "ok"}


@app.get("/")
@app.get("/health")
async def root():
    # P-22: las sondas (inspección de esquema y probe contra Supabase) son I/O
    # síncronas; se ejecutan en un hilo aparte para que /health no bloquee el
    # event loop (y con él /live, que es lo que Render sondea para no reiniciar).
    from fastapi.concurrency import run_in_threadpool
    from src.database import db_diagnostic, db_schema_diagnostic
    from src.engine.audit_agent import audit_agent_enabled
    from src.utils.supabase_storage import storage_diagnostic

    schema = await run_in_threadpool(db_schema_diagnostic)
    storage = await run_in_threadpool(storage_diagnostic)
    return {
        "status": "online",
        "message": "Agente BI API is running (Modular Mode)",
        "version": "1.0.0",
        # Permite verificar desde fuera que el despliegue activo tiene Fase 2.
        "features": {"audit_agent": audit_agent_enabled()},
        # Solo tipo de dato y si hay almacenamiento en nubeConfigured: permite
        # verificar desde fuera que los datos sobreviven a un reinicio. Nunca se
        # expone host, usuario, bucket ni credenciales.
        "database": {
            **db_diagnostic(),
            "schema": schema,
        },
        "storage": {k: v for k, v in storage.items() if k != "bucket"},
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
    # Sin reload se pasa el objeto app directamente: usar el string "main:app"
    # obligaba a reimportar todo main.py (y con el, pandas/matplotlib/statsmodels/
    # supabase...) una segunda vez, duplicando el arranque hasta ~35 s y haciendo
    # que Render perdiera la ventana de deteccion de puerto.
    target = "main:app" if reload_enabled else app
    uvicorn.run(target, host="0.0.0.0", port=port, reload=reload_enabled)


