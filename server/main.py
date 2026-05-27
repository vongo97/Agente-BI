import uvicorn
import logging
import warnings
from fastapi import FastAPI

# Silenciar advertencias de formato de fecha
warnings.filterwarnings("ignore", category=UserWarning)
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Cargar variables de entorno lo antes posible
load_dotenv()

# Importar routers, utilidades y rate limiting
from src.database import init_db
# Importar routers, utilidades y rate limiting
from src.database import init_db
from src.utils.limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

app = FastAPI(title="Vektra BI API (Modular)")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from src.routers import auth, data, analysis, dashboard, exports, simulation, visual_summary

# Configuración de Logs Estructurados (Fase 2)
from src.utils.logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

# Configurar CORS (Seguridad Fase 1)
ALLOWED_ORIGINS = [
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "https://agente-bi.vercel.app", # Ejemplo de dominio prod
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def catch_exceptions_middleware(request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"GLOBAL 500 ERROR: {str(e)}\n{error_trace}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal Server Error: {str(e)}", "traceback": error_trace}
        )

# Registrar Routers con Versionado (Fase 2)
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
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
