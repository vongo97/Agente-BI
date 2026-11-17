import uvicorn
import logging
import os
import re
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
from slowapi.errors import RateLimitExceeded

app = FastAPI(title="Vektra BI API (Modular)")
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request, exc: RateLimitExceeded):
    """P-76: el límite de peticiones debe explicar qué hacer, no soltar un código.

    El manejador por defecto de slowapi devuelve el detalle crudo del límite
    ("5 per 1 minute"), que el cliente muestra tal cual. Durante las pruebas
    manuales —subir varios archivos seguidos— eso le llega al usuario como un
    error sin explicación, indistinguible de un fallo real del servidor.

    Aquí se traduce a un mensaje accionable y se añade `Retry-After` para que
    el cliente (y cualquier proxy) sepa cuándo reintentar.
    """
    detail = getattr(exc, "detail", None) or str(exc)
    retry_after = 60
    match = re.search(r"(\d+)\s+per\s+(\d+)\s+(minute|hour|second|day)", str(detail), re.IGNORECASE)
    if match:
        cantidad, unidad = int(match.group(1)), match.group(3).lower()
        retry_after = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}.get(unidad, 60)
        if unidad == "minute":
            # El cubo se vacía cada minuto: espera media vuelta del intervalo.
            retry_after = max(1, round(60 / max(cantidad, 1)))
    logging.getLogger(__name__).warning(
        "RATE_LIMITED path=%s detalle=%s retry_after=%ss",
        getattr(request, "url", None).path if request else "?",
        detail,
        retry_after,
    )
    return JSONResponse(
        status_code=429,
        content={
            "detail": (
                f"Demasiadas peticiones seguidas (máximo {detail}). "
                f"Espera unos {retry_after} segundos e inténtalo de nuevo."
            )
        },
        headers={"Retry-After": str(retry_after)},
    )

from src.routers import auth, data, analysis, dashboard, exports, simulation, visual_summary, reports
from src.utils.common import request_var, is_development_mode

# Configuración de Logs Estructurados
from src.utils.logging_config import setup_logging, request_id_var, new_request_id
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

# ── Middleware: Request ID (P-36) ─────────────────────────────────────────────
# La cabecera `X-Request-Id` ya estaba declarada en CORS pero nunca se generaba.
# Ahora cada petición recibe un id de correlación: si el cliente lo envía, se
# respeta; si no, se genera uno. El id viaja en un ContextVar para que cualquier
# capa (incluidos los `except` que ignoran una excepción) pueda adjuntarlo al log
# y así unir "un error en un log" con "la petición que lo provocó".
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")


@app.middleware("http")
async def request_id_middleware(request, call_next):
    incoming = request.headers.get("X-Request-Id")
    # Solo se acepta un id externo si es un token opaco y acotado (UUIDs, hex,
    # "cliente-123"...); si no, se genera uno para no propagar basura al log.
    rid = incoming if (incoming and _REQUEST_ID_RE.match(incoming)) else new_request_id()
    token = request_id_var.set(rid)
    try:
        response = await call_next(request)
        response.headers["X-Request-Id"] = rid
        return response
    finally:
        request_id_var.reset(token)


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

# ── P-49: auditoría del almacenamiento al arrancar ───────────────────────────
# Sin SUPABASE_* el servicio arranca, pero cada archivo subido se queda en el
# disco del contenedor: en Render ese disco es efímero, así que el archivo se
# pierde en el siguiente reinicio. El aviso tiene que salir AL ARRANCAR, no
# solo cuando alguien sube un archivo y lee el error.
#
# Se distinguen los dos casos que se confundían:
#   - credenciales ausentes  -> no hay nube configurada (modo local).
#   - credenciales presentes pero el bucket no responde -> la nube está mal
#     configurada (o caída), que es un fallo de configuración, no "modo local".
from src.utils.supabase_storage import storage_configured  # noqa: E402

if not storage_configured():
    logger.warning(
        "CONFIG: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY no configuradas -> los "
        "archivos y las sesiones se guardan SOLO en el disco local (cifrado), que "
        "en Render se pierde en cada reinicio. /upload seguirá funcionando, pero "
        "con 'persisted=false'. Define ambas variables para tener persistencia."
    )
else:
    logger.info("CONFIG: almacenamiento en nube configurado")

# Registrar Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(data.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(exports.router, prefix="/api/v1")
app.include_router(simulation.router, prefix="/api/v1")
app.include_router(visual_summary.router, prefix="/api/v1")
# P-23: el router de reports estaba implementado pero nunca se montaba, así que
# el endpoint /report/kpi-summary no existía y sus consumidores en el cliente
# (KpiCards, AnomalyAlert) quedaban sin datos.
app.include_router(reports.router, prefix="/api/v1")

# Inicializar Base de Datos de forma segura
try:
    init_db()
except Exception as e:
    # P-19: si la BD configurada está rota o es inalcanzable, `init_db` aborta
    # con un RuntimeError claro. Tragar ese error y seguir sirviendo sería
    # exactamente el fallo que P-19 describe: el servicio "arranca" pero pierde
    # datos y responde 500 en cada endpoint que toca la BD.
    logger.error("No se pudo completar init_db al iniciar: %s", e)
    if is_development_mode() and os.getenv("RENDER", "false").strip().lower() != "true":
        logger.warning(
            "MODO DESARROLLO: se continúa sin base de datos inicializada. "
            "Los endpoints que usan la BD fallarán hasta corregir la configuración."
        )
    else:
        raise

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


