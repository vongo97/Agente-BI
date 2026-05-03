from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
import json
import logging
from src.database import get_db, Chat, Message, DashboardItem
from src.engine.bi_analyst import generate_auto_dashboard
from src.engine.executor import execute_analysis
from src.utils.common import check_authorization, get_user_data
import pandas as pd

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Dashboard"])

@router.get("/history")
async def get_history(user_id: str, db: Session = Depends(get_db)):
    check_authorization(user_id)
    chats = db.query(Chat).filter(Chat.user_id == user_id).order_by(desc(Chat.created_at)).all()
    return [{"id": c.id, "title": c.title, "created_at": c.created_at} for c in chats]

@router.get("/history/{chat_id}")
async def get_chat_details(chat_id: int, user_id: str, db: Session = Depends(get_db)):
    check_authorization(user_id)
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    
    messages = []
    for m in chat.messages:
        messages.append({
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "fig": json.loads(m.figure_json) if m.figure_json else None
        })
    
    source_info = None
    if chat.data_source:
        source_info = {
            "id": chat.data_source.id,
            "name": chat.data_source.name,
            "type": chat.data_source.type,
            "url": chat.data_source.url,
            "columns": json.loads(chat.data_source.columns) if chat.data_source.columns else []
        }

    return {
        "id": chat.id, 
        "title": chat.title, 
        "messages": messages,
        "data_source": source_info
    }

@router.post("/dashboard/pin")
async def pin_to_dashboard(
    user_id: str = Form(...),
    chat_id: int = Form(...),
    message_id: int = Form(...),
    db: Session = Depends(get_db)
):
    check_authorization(user_id)
    existing = db.query(DashboardItem).filter(
        DashboardItem.user_id == user_id, 
        DashboardItem.message_id == message_id
    ).first()
    
    if existing:
        return {"message": "Ya está en el dashboard"}
    
    new_item = DashboardItem(user_id=user_id, chat_id=chat_id, message_id=message_id)
    db.add(new_item)
    db.commit()
    return {"message": "Anclado al dashboard con éxito"}

@router.get("/dashboard")
async def get_dashboard(user_id: str, db: Session = Depends(get_db)):
    check_authorization(user_id)
    items = db.query(DashboardItem).filter(DashboardItem.user_id == user_id).all()
    results = []
    for item in items:
        if not item.chat or not item.message:
            continue
        try:
            results.append({
                "id": item.id,
                "chat_title": item.chat.title,
                "content": item.message.content,
                "fig": json.loads(item.message.figure_json) if item.message.figure_json else None,
                "pinned_at": item.pinned_at
            })
        except:
            continue
    return results

@router.delete("/dashboard/{item_id}")
async def unpin_from_dashboard(item_id: int, user_id: str, db: Session = Depends(get_db)):
    check_authorization(user_id)
    item = db.query(DashboardItem).filter(DashboardItem.id == item_id, DashboardItem.user_id == user_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    db.delete(item)
    db.commit()
    return {"message": "Eliminado del dashboard"}

@router.post("/auto-dashboard")
async def auto_dashboard(
    user_id: str = Form(...), 
    api_key: str = Form(...),
    data_source_id: Optional[int] = Form(None),
    provider: str = Form("gemini"),
    mistral_key: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    check_authorization(user_id)
    session_data = get_user_data(user_id)
    
    if not session_data and data_source_id:
        from src.database import DataSource
        from src.utils.common import load_source_to_session
        source = db.query(DataSource).filter(DataSource.id == data_source_id, DataSource.user_id == user_id).first()
        if source and load_source_to_session(user_id, source):
            session_data = get_user_data(user_id)

    if not session_data:
         raise HTTPException(status_code=400, detail="Se requieren datos activos (SQL o Archivo) para generar un Auto-Dashboard.")
         
    # El origen puede ser un motor SQL o un diccionario de DataFrames
    data_source_obj = session_data["data"]
    if session_data["type"] == "file":
        # Usamos el primer DataFrame si hay varios para el dashboard base
        data_source_obj = next(iter(session_data["data"].values()))
    
    results = generate_auto_dashboard(data_source_obj, api_key, provider, mistral_key)
    from src.utils.common import json_serializable
    return json_serializable({"status": "success", "dashboard": results})

@router.post("/dashboard/filter")
async def filter_dashboard(
    user_id: str = Form(...),
    filters_json: str = Form(...), # JSON string: {"col": "val"}
    db: Session = Depends(get_db)
):
    check_authorization(user_id)
    try:
        filters = json.loads(filters_json)
    except:
        raise HTTPException(status_code=400, detail="JSON de filtros inválido")

    session_data = get_user_data(user_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="No hay datos cargados en la sesión")

    context = session_data["data"]
    data_type = session_data["type"]
    var_name = "dfs" if data_type == "file" else "engine"

    # Aplicar filtros al contexto (solo para modo file por ahora)
    if data_type == "file":
        filtered_context = {}
        for name, df in context.items():
            if isinstance(df, pd.DataFrame):
                new_df = df.copy()
                for col, val in filters.items():
                    if col in new_df.columns and val is not None and val != "":
                        # Soporte para filtrado simple
                        new_df = new_df[new_df[col] == val]
                filtered_context[name] = new_df
            else:
                filtered_context[name] = df
    else:
        # TODO: Implementar filtrado SQL dinámico inyectando cláusulas WHERE
        filtered_context = context

    items = db.query(DashboardItem).filter(DashboardItem.user_id == user_id).all()
    results = []
    
    for item in items:
        if not item.message or not item.message.analysis_code:
            continue
        
        try:
            # Re-ejecutar el código original sobre los datos filtrados
            # execute_analysis espera el raw_response con bloques de código
            _, fig = execute_analysis(filtered_context, item.message.analysis_code, var_name)
            
            results.append({
                "id": item.id,
                "fig": json.loads(fig.to_json()) if fig else None
            })
        except Exception as e:
            logger.error(f"Error re-filtrando item {item.id}: {e}")
            continue

    return {"status": "success", "updated_items": results}
