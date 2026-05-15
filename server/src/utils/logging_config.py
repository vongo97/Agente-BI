import logging
import json
import datetime
import sys
from typing import Any

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
    Configura el sistema de logs global del servidor.
    """
    root_logger = logging.getLogger()
    
    # Evitar duplicados si se llama varias veces
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.setLevel(logging.INFO)

    # Handler para Consola (Legible)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
    ))
    root_logger.addHandler(console_handler)

    # Handler para Archivo (JSON Estructurado)
    file_handler = logging.FileHandler("server_structured.log")
    file_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(file_handler)

    # Silenciar logs ruidosos de librerías
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logging.info("Sistema de logs estructurados inicializado.")
