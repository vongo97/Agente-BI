from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
import json
import logging
from src.database import get_db, Chat, Message, DashboardItem
from src.engine.bi_analyst import generate_auto_dashboard
from src.engine.executor import execute_analysis
from src.utils.common import check_authorization, get_user_data, get_authenticated_user
from src.utils.limiter import limiter
import pandas as pd

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Dashboard"])

@router.get("/history")
async def get_history(db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    chats = db.query(Chat).filter(Chat.user_id == authenticated_user).order_by(desc(Chat.created_at)).all()
    return [{"id": c.id, "title": c.title, "created_at": c.created_at} for c in chats]

@router.get("/history/{chat_id}")
async def get_chat_details(chat_id: int, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == authenticated_user).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")
    
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
    chat_id: int = Form(...),
    message_id: int = Form(...),
    db: Session = Depends(get_db)
):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == authenticated_user).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")
        
    message = db.query(Message).filter(Message.id == message_id, Message.chat_id == chat_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")

    existing = db.query(DashboardItem).filter(
        DashboardItem.user_id == authenticated_user, 
        DashboardItem.message_id == message_id
    ).first()
    
    if existing:
        return {"message": "Ya está en el dashboard"}
    
    new_item = DashboardItem(user_id=authenticated_user, chat_id=chat_id, message_id=message_id)
    db.add(new_item)
    db.commit()
    return {"message": "Anclado al dashboard con éxito"}

@router.get("/dashboard")
async def get_dashboard(db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    items = db.query(DashboardItem).filter(DashboardItem.user_id == authenticated_user).all()
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
@limiter.limit("15/minute")
async def unpin_from_dashboard(request: Request, item_id: int, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    try:
        item = db.query(DashboardItem).filter(DashboardItem.id == item_id, DashboardItem.user_id == authenticated_user).first()
        if not item:
            raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")
        db.delete(item)
        db.commit()
        return {"message": "Eliminado del dashboard"}
    except HTTPException as he:
        raise he
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("Error al desanclar del dashboard: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error interno al desanclar el elemento.")

@router.post("/auto-dashboard")
@limiter.limit("5/minute")
@limiter.limit("20/hour")
async def auto_dashboard(
    request: Request,
    api_key: str = Form(...),
    data_source_id: Optional[int] = Form(None),
    provider: str = Form("gemini"),
    mistral_key: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    session_data = get_user_data(authenticated_user)
    
    if not session_data and data_source_id:
        from src.database import DataSource
        from src.utils.common import load_source_to_session
        source = db.query(DataSource).filter(DataSource.id == data_source_id, DataSource.user_id == authenticated_user).first()
        if source and load_source_to_session(authenticated_user, source):
            session_data = get_user_data(authenticated_user)

    if not session_data:
         raise HTTPException(status_code=400, detail="Se requieren datos activos (SQL o Archivo) para generar un Auto-Dashboard.")
         
    # --- AUTO-RECUPERACIÓN DE LLAVES CIFRADAS ---
    if len(api_key) < 10 or "..." in api_key or (provider == "mistral" and (not mistral_key or len(mistral_key) < 10 or "..." in mistral_key)):
        from src.database import UserConfig
        from src.utils.security import decrypt_key
        user_config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
        if user_config:
            if (len(api_key) < 10 or "..." in api_key) and user_config.gemini_key:
                api_key = decrypt_key(user_config.gemini_key)
            if provider == "mistral" and (not mistral_key or len(mistral_key) < 10 or "..." in mistral_key) and user_config.mistral_key:
                mistral_key = decrypt_key(user_config.mistral_key)
    else:
        from src.utils.security import decrypt_key
        api_key = decrypt_key(api_key)
        if mistral_key:
            mistral_key = decrypt_key(mistral_key)
         
    # Validar que las llaves descifradas no sean vacías o None si el proveedor las requiere
    if provider == "gemini" and not api_key:
        raise HTTPException(
            status_code=400,
            detail="Clave API de Gemini no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes."
        )
    elif provider == "mistral" and not mistral_key:
        raise HTTPException(
            status_code=400,
            detail="Clave API de Mistral no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes."
        )
    elif provider == "hybrid":
        if not api_key:
            raise HTTPException(status_code=400, detail="Clave API de Gemini no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
        if not mistral_key:
            raise HTTPException(status_code=400, detail="Clave API de Mistral no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")

    try:
        # El origen puede ser un motor SQL o un diccionario de DataFrames
        data_source_obj = session_data["data"]
        if session_data["type"] == "file":
            # Priorizar el archivo seleccionado (data_source_id) si existe
            if data_source_id:
                from src.database import DataSource
                source_obj = db.query(DataSource).filter(DataSource.id == data_source_id, DataSource.user_id == authenticated_user).first()
                if source_obj:
                    safe_name = "".join([c if c.isalnum() else "_" for c in source_obj.name.split('.')[0]])
                    if safe_name in session_data["data"]:
                        data_source_obj = session_data["data"][safe_name]
                    else:
                        # Fallback si no está en memoria por alguna razón
                        data_source_obj = next(iter(session_data["data"].values()))
                else:
                    raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")
            else:
                # Usamos el primer DataFrame si hay varios para el dashboard base
                data_source_obj = next(iter(session_data["data"].values()))
        
        results = generate_auto_dashboard(data_source_obj, api_key, provider, mistral_key)
        from src.utils.common import json_serializable
        return json_serializable({"status": "success", "dashboard": results})
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("Error en auto_dashboard: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error interno al generar el panel automático.")

@router.post("/dashboard/filter")
@limiter.limit("10/minute")
async def filter_dashboard(
    request: Request,
    filters_json: str = Form(...), # JSON string: {"col": "val"}
    db: Session = Depends(get_db)
):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    try:
        filters = json.loads(filters_json)
    except:
        raise HTTPException(status_code=400, detail="JSON de filtros inválido")

    try:
        session_data = get_user_data(authenticated_user)
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

        items = db.query(DashboardItem).filter(DashboardItem.user_id == authenticated_user).all()
        results = []
        
        for item in items:
            if not item.message or not item.message.analysis_code:
                continue
            
            try:
                # Re-ejecutar el código original sobre los datos filtrados
                # execute_analysis espera el raw_response con bloques de código
                _, fig = await execute_analysis(filtered_context, item.message.analysis_code, var_name)
                
                results.append({
                    "id": item.id,
                    "fig": json.loads(fig.to_json()) if fig else None
                })
            except Exception as e:
                from src.utils.logging_config import safe_error_message
                logger.error("Error re-filtrando item %d: %s", item.id, safe_error_message(e))
                continue

        return {"status": "success", "updated_items": results}
    except HTTPException as he:
        raise he
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("Error al filtrar panel: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error interno al filtrar el panel.")
