import uvicorn
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Cargar variables de entorno lo antes posible
load_dotenv()

# Importar routers y utilidades
from src.database import init_db
from src.routers import auth, data, analysis, dashboard, exports, simulation

# Configuración de Logs
logging.basicConfig(
    filename='debug_server.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Vektra BI API (Modular)")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar Routers
app.include_router(auth.router)
app.include_router(data.router)
app.include_router(analysis.router)
app.include_router(dashboard.router)
app.include_router(exports.router)
app.include_router(simulation.router)

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
