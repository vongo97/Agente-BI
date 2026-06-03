import json
import os
import logging
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
from src.database import get_db, Chat, Message, UserConfig
from src.engine.bi_analyst import analyze_data, execute_analysis, suggest_questions, validate_data_quality
from src.utils.common import check_authorization, get_user_data, get_authenticated_user
from src.utils.security import decrypt_key

from src.utils.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Analysis"])

@router.post("/analyze")
@limiter.limit("5/minute")
@limiter.limit("30/hour")
async def analyze(
    request: Request,
    query: str = Form(...),
    api_key: str = Form(...),
    user_id: Optional[str] = Form(None),
    chat_id: Optional[int] = Form(None),
    data_source_id: Optional[int] = Form(None),
    provider: str = Form("gemini"),
    mistral_key: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    
    # --- AUTO-RECUPERACIÓN DE LLAVES CIFRADAS ---
    # Si las llaves vienen vacías o cortas, intentamos sacarlas de la DB del usuario
    if len(api_key) < 10 or (provider == "mistral" and (not mistral_key or len(mistral_key) < 10)):
        user_config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
        if user_config:
            if len(api_key) < 10 and user_config.gemini_key:
                api_key = decrypt_key(user_config.gemini_key)
            if provider == "mistral" and (not mistral_key or len(mistral_key) < 10) and user_config.mistral_key:
                mistral_key = decrypt_key(user_config.mistral_key)
    else:
        # Si vienen del frontend pero están cifradas (empiezan por gAAAA), las desciframos
        api_key = decrypt_key(api_key)
        if mistral_key: mistral_key = decrypt_key(mistral_key)
    
    # Filtro de saludos
    greetings = ["hola", "hi", "hey", "buenos dias", "buenas tardes", "buenas noches"]
    if query.strip().lower() in greetings:
        msg = "¡Hola! Soy Vektra. ¿Qué te gustaría analizar de tus datos hoy?"
        new_msg = Message(chat_id=chat_id, role="assistant", content=msg)
        db.add(new_msg); db.commit()
        return {"analysis": msg, "chat_id": chat_id, "message_id": new_msg.id}

    # Si no hay data_source_id pero hay chat_id, intentar recuperarlo del chat
    if chat_id and not data_source_id:
        db_chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == authenticated_user).first()
        if db_chat and db_chat.data_source_id:
            data_source_id = db_chat.data_source_id
 
    # DIAGNÓSTICO — pasan por el filtro de secretos del logger
    logger.debug("Analyze Request: user=%s, chat=%s, source=%s, provider=%s",
                 authenticated_user, chat_id, data_source_id, provider)
    
    session_data = get_user_data(authenticated_user, chat_id)
    logger.debug("Session Data found: %s", session_data is not None)
    
    # Verificar si la fuente solicitada está en el pool actual
    is_source_in_pool = session_data is not None and data_source_id and (
        session_data.get("source_id") == data_source_id or 
        data_source_id in session_data.get("sources", [])
    )
    
    if session_data is not None and data_source_id and not is_source_in_pool:
        logger.debug("Source Mismatch: request=%s not in pool %s",
                     data_source_id, session_data.get('sources', []))
        # Solo descartar la sesión si el pool está completamente vacío.
        has_data = bool(session_data.get("data"))
        if not has_data:
            session_data = None
        # Si has_data == True, conservamos session_data para que la segunda pregunta
        # pueda acceder a los archivos que ya estaban en el pool.

    if session_data is None:
        # Intentar auto-cargar desde DataSource si tenemos el ID
        if data_source_id:
            logger.debug("Attempting auto-load for source %s", data_source_id)
            from src.database import DataSource
            from src.utils.common import load_source_to_session
            source = db.query(DataSource).filter(DataSource.id == data_source_id, DataSource.user_id == authenticated_user).first()
            if source:
                success = load_source_to_session(authenticated_user, source, chat_id)
                logger.debug("Auto-load success: %s", success)
                if success:
                    session_data = get_user_data(authenticated_user, chat_id)
        
        if not session_data:
            logger.warning("No session data found or loaded for user (source=%s).", data_source_id)
            raise HTTPException(status_code=400, detail="No hay datos cargados para analizar. Por favor selecciona una fuente de datos.")
    
    try:
        # Determinar el tipo de dato y la variable
        data_type = session_data["type"]
        data_var = "dfs" if data_type == "file" else "engine"

        # Determinar el nombre de la fuente primaria para el aislamiento de contexto
        primary_source_name = None
        if data_source_id:
            from src.database import DataSource
            source_obj = db.query(DataSource).filter(DataSource.id == data_source_id).first()
            if source_obj:
                primary_source_name = "".join([c if c.isalnum() else "_" for c in source_obj.name.split('.')[0]])
        
        # --- FILTRO DE CALIDAD ---
        is_valid, reason = validate_data_quality(session_data["data"])
        if not is_valid:
            content = f"### ⚠️ Lo sentimos, archivo no compatible\n{reason}\n\n**Sugerencia:** Por favor, asegúrate de subir un archivo con datos estructurados (filas y columnas) que contenga al menos una columna de números (métricas)."
            new_msg = Message(chat_id=chat_id, role="assistant", content=content)
            db.add(new_msg); db.commit()
            return {"analysis": content, "chat_id": chat_id, "message_id": new_msg.id}
        
        # 1. Obtener análisis, gráfico y código de la IA
        output_text, fig, raw_response = await analyze_data(
            session_data["data"], 
            query, 
            api_key, 
            mode=data_type, 
            provider=provider, 
            mistral_key=mistral_key,
            primary_source_name=primary_source_name
        )
        
        fig_json = json.loads(fig.to_json()) if fig and hasattr(fig, 'to_json') else fig
            
        # Persistencia
        if chat_id:
            db_chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == authenticated_user).first()
        else:
            db_chat = Chat(
                user_id=authenticated_user, 
                title=query[:50] + "...",
                data_source_id=data_source_id
            )
            db.add(db_chat)
            db.commit()
            db.refresh(db_chat)
            # Promocionar los datos de la sesión activa al nuevo chat ID
            from src.utils.common import promote_active_session
            promote_active_session(authenticated_user, db_chat.id)
        
        user_msg = Message(chat_id=db_chat.id, role="user", content=query)
        db.add(user_msg)
        
        from src.utils.common import SafeJSONEncoder, json_serializable
        assistant_msg = Message(
            chat_id=db_chat.id, 
            role="assistant", 
            content=output_text,
            figure_json=json.dumps(fig_json, cls=SafeJSONEncoder) if fig_json else None,
            analysis_code=raw_response
        )
        db.add(assistant_msg)
        db.commit()
            
        from src.utils.common import json_serializable
        return json_serializable({
            "chat_id": db_chat.id,
            "message_id": assistant_msg.id,
            "analysis": output_text,
            "figure": fig_json,
            "code": raw_response
        })
    except Exception as e:
        is_render = os.getenv("RENDER", "false").lower() == "true"
        from src.utils.logging_config import safe_error_message
        clean_msg = safe_error_message(e)
        if not is_render:
            logger.exception("ERROR 500 /analyze [%s]: %s", type(e).__name__, clean_msg)
        else:
            logger.error("ERROR 500 /analyze [%s]: %s", type(e).__name__, clean_msg)
        raise HTTPException(status_code=500, detail="Error interno del servidor al procesar el análisis de datos.")

@router.post("/suggest-questions")
@limiter.limit("10/minute")
@limiter.limit("60/hour")
def get_suggestions(
    request: Request,
    user_id: Optional[str] = Form(None), 
    api_key: str = Form(...),
    chat_id: Optional[int] = Form(None), # AÑADIDO
    data_source_id: Optional[int] = Form(None),
    provider: str = Form("gemini"),
    mistral_key: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    # Si no viene mistral_key, intentar recuperarla de la base de datos
    if not mistral_key:
        from src.database import UserConfig
        config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
        if config:
            mistral_key = config.mistral_key
 
    session_data = get_user_data(authenticated_user, chat_id)
    
    # VALIDACIÓN DE FUENTE: Si el ID solicitado no está en el pool, forzar recarga
    is_source_in_pool = session_data and data_source_id and (
        session_data.get("source_id") == data_source_id or 
        data_source_id in session_data.get("sources", [])
    )
 
    if session_data and data_source_id and not is_source_in_pool:
        session_data = None
 
    if not session_data:
        # Intentar auto-cargar desde DataSource si tenemos el ID
        if data_source_id:
            from src.database import DataSource
            from src.utils.common import load_source_to_session
            source = db.query(DataSource).filter(DataSource.id == data_source_id, DataSource.user_id == authenticated_user).first()
            if source and load_source_to_session(authenticated_user, source, chat_id):
                session_data = get_user_data(authenticated_user, chat_id)

    if not session_data:
        raise HTTPException(status_code=404, detail="No hay datos cargados para generar sugerencias.")
    
    suggestions = []
    try:
        context = session_data["data"]
        
        # Determinar el nombre de la fuente primaria para el aislamiento de contexto
        primary_source_name = None
        if data_source_id:
            from src.database import DataSource
            source_obj = db.query(DataSource).filter(DataSource.id == data_source_id).first()
            if source_obj:
                primary_source_name = "".join([c if c.isalnum() else "_" for c in source_obj.name.split('.')[0]])

        if session_data["type"] == "sql":
            from src.connectors.data_connectors import get_db_schema
            context = get_db_schema(session_data["data"])

        suggestions = suggest_questions(
            context, 
            api_key, 
            mode=session_data["type"], 
            provider=provider, 
            mistral_key=mistral_key,
            primary_source_name=primary_source_name
        )
    except Exception as e:
        logger.warning("Suggest Questions error (non-critical): %s", type(e).__name__)
        suggestions = ["¿Qué insights hay en los datos?"]
        
    return {"suggestions": suggestions}

@router.post("/detect-anomalies")
async def detect_anomalies():
    return {
        "analysis": "### 🚀 Detective de Datos: Próximamente\nEstamos refinando el motor de auditoría proactiva."
    }

@router.post("/generate-report-summary")
@limiter.limit("5/minute")
def get_report_summary(
    request: Request,
    query: str = Form(...),
    api_key: str = Form(...),
    user_id: Optional[str] = Form(None),
    provider: str = Form("gemini"),
    mistral_key: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    session_data = get_user_data(authenticated_user)
    
    # Generar el resumen usando el motor de IA
    from src.engine.bi_analyst import generate_report_summary
    
    context_data = session_data["data"] if session_data else None
    summary = generate_report_summary(
        query=query,
        api_key=api_key,
        context_data=context_data,
        provider=provider,
        mistral_key=mistral_key
    )
    
    return {"summary": summary}
