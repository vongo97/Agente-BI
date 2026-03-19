from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
import json
import logging
from src.database import get_db, Chat, Message, DashboardItem
from src.engine.bi_analyst import generate_auto_dashboard
from src.utils.common import check_authorization, get_user_data

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

    if not session_data or session_data["type"] != "file":
         raise HTTPException(status_code=400, detail="Se requieren datos de archivo para generar un Auto-Dashboard.")
         
    df = next(iter(session_data["data"].values()))
    results = generate_auto_dashboard(df, api_key, provider, mistral_key)
    return {"status": "success", "dashboard": results}
