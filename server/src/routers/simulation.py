from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
from ..engine import bi_analyst
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class SimulationQuery(BaseModel):
    query: str
    user_id: str
    api_key: str
    mistral_key: Optional[str] = None
    provider: str = "gemini"
    session_files: List[str] = [] # Nombres de los archivos a incluir en la simulación

@router.post("/simulate")
async def run_simulation(data: SimulationQuery):
    try:
        from ..connectors import data_connectors
        
        # Cargar contexto de múltiples archivos para el simulador
        context = data_connectors.get_user_context(data.user_id)
        
        # Si el usuario especificó archivos, filtramos el contexto
        if data.session_files:
            filtered_context = {
                name: df for name, df in context.items() 
                if name in data.session_files
            }
            if not filtered_context:
                raise HTTPException(status_code=404, detail="No se encontraron los archivos especificados para la simulación")
            context = filtered_context

        # El simulador siempre usa el modo "file" (Pandas) por ahora
        response = bi_analyst.analyze_data(
            data_context=context,
            query=f"[MODO SIMULADOR: ENSAYO DEL FUTURO] {data.query}",
            api_key=data.api_key,
            mistral_key=data.mistral_key,
            provider=data.provider,
            mode="file"
        )
        
        return {"result": response}
    except Exception as e:
        logger.error(f"Error en simulación: {e}")
        raise HTTPException(status_code=500, detail=str(e))
