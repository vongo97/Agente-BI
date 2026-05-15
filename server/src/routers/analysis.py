import json
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
from src.database import get_db, Chat, Message, UserConfig
from src.engine.bi_analyst import analyze_data, execute_analysis, suggest_questions, validate_data_quality
from src.utils.common import check_authorization, get_user_data
from src.utils.security import decrypt_key

from src.utils.limiter import limiter

router = APIRouter(tags=["Analysis"])

@router.post("/analyze")
@limiter.limit("5/minute")
def analyze(
    request: Request,
    query: str = Form(...),
    api_key: str = Form(...),
    user_id: str = Form(...),
    chat_id: Optional[int] = Form(None),
    data_source_id: Optional[int] = Form(None),
    provider: str = Form("gemini"),
    mistral_key: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    check_authorization(user_id)
    
    # --- AUTO-RECUPERACIÓN DE LLAVES CIFRADAS ---
    # Si las llaves vienen vacías o cortas, intentamos sacarlas de la DB del usuario
    if len(api_key) < 10 or (provider == "mistral" and (not mistral_key or len(mistral_key) < 10)):
        user_config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
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
        db_chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
        if db_chat and db_chat.data_source_id:
            data_source_id = db_chat.data_source_id

    # DIAGNÓSTICO
    print(f"[DEBUG] Analyze Request: user={user_id}, chat={chat_id}, source={data_source_id}, provider={provider}")
    
    session_data = get_user_data(user_id, chat_id)
    print(f"[DEBUG] Session Data found: {session_data is not None}")
    
    # Verificar si la fuente solicitada está en el pool actual
    is_source_in_pool = session_data is not None and data_source_id and (
        session_data.get("source_id") == data_source_id or 
        data_source_id in session_data.get("sources", [])
    )
    
    if session_data is not None and data_source_id and not is_source_in_pool:
        print(f"[DEBUG] Source Mismatch: request={data_source_id} not in pool {session_data.get('sources', [])}")
        session_data = None
        
    if session_data is None:
        # Intentar auto-cargar desde DataSource si tenemos el ID
        if data_source_id:
            print(f"[DEBUG] Attempting auto-load for source {data_source_id}")
            from src.database import DataSource
            from src.utils.common import load_source_to_session
            source = db.query(DataSource).filter(DataSource.id == data_source_id, DataSource.user_id == user_id).first()
            if source:
                success = load_source_to_session(user_id, source, chat_id)
                print(f"[DEBUG] Auto-load success: {success}")
                if success:
                    session_data = get_user_data(user_id, chat_id)
        
        if not session_data:
            print("[DEBUG] CRITICAL: No session data could be found or loaded.")
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
        output_text, fig, raw_response = analyze_data(
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
            db_chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
        else:
            db_chat = Chat(
                user_id=user_id, 
                title=query[:50] + "...",
                data_source_id=data_source_id
            )
            db.add(db_chat)
            db.commit()
            db.refresh(db_chat)
            # Promocionar los datos de la sesión activa al nuevo chat ID
            from src.utils.common import promote_active_session
            promote_active_session(user_id, db_chat.id)
        
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
        import traceback
        traceback.print_exc()
        print(f"[ERROR 500] {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/suggest-questions")
@limiter.limit("10/minute")
def get_suggestions(
    request: Request,
    user_id: str = Form(...), 
    api_key: str = Form(...),
    chat_id: Optional[int] = Form(None), # AÑADIDO
    data_source_id: Optional[int] = Form(None),
    provider: str = Form("gemini"),
    mistral_key: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    # Si no viene mistral_key, intentar recuperarla de la base de datos
    if not mistral_key:
        from src.database import UserConfig
        config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
        if config:
            mistral_key = config.mistral_key

    session_data = get_user_data(user_id, chat_id)
    
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
            source = db.query(DataSource).filter(DataSource.id == data_source_id, DataSource.user_id == user_id).first()
            if source and load_source_to_session(user_id, source, chat_id):
                session_data = get_user_data(user_id, chat_id)

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
        print(f"[ERROR] Suggest Questions: {e}")
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
    user_id: str = Form(...),
    provider: str = Form("gemini"),
    mistral_key: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    check_authorization(user_id)
    session_data = get_user_data(user_id)
    
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
