import json
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from src.database import get_db, Chat, Message
from src.engine.bi_analyst import analyze_data, execute_analysis, suggest_questions
from src.utils.common import check_authorization, get_user_data

router = APIRouter(tags=["Analysis"])

@router.post("/analyze")
async def analyze(
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
    
    # Filtro de saludos
    greetings = ["hola", "hi", "hey", "buenos dias", "buenas tardes", "buenas noches"]
    if query.lower().strip().replace("!", "").replace("?", "") in greetings:
        return {
            "chat_id": None,
            "analysis": "¡Hola! 👋 Soy tu Analista BI. ¿Qué quieres analizar hoy?",
            "figure": None,
            "code": "# Saludo"
        }

    # Si no hay data_source_id pero hay chat_id, intentar recuperarlo del chat
    if chat_id and not data_source_id:
        db_chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
        if db_chat and db_chat.data_source_id:
            data_source_id = db_chat.data_source_id

    # DIAGNÓSTICO
    print(f"[DEBUG] Analyze Request: user={user_id}, chat={chat_id}, source={data_source_id}, provider={provider}")
    
    session_data = get_user_data(user_id, chat_id)
    print(f"[DEBUG] Session Data found: {True if session_data else False}")
    
    # VALIDACIÓN DE FUENTE: Si el ID solicitado no coincide con lo cargado, forzar recarga
    if session_data and data_source_id and session_data.get("source_id") != data_source_id:
        print(f"[DEBUG] Source Mismatch: session={session_data.get('source_id')} vs request={data_source_id}")
        session_data = None
        
    if not session_data:
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
        
        # 1. Obtener código de la IA
        raw_response = analyze_data(session_data["data"], query, api_key, mode=data_type, provider=provider, mistral_key=mistral_key)
        
        # 2. Ejecutar análisis final
        output_text, fig = execute_analysis(session_data["data"], raw_response, data_var)
        
        fig_json = json.loads(fig.to_json()) if fig else None
            
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
        
        assistant_msg = Message(
            chat_id=db_chat.id, 
            role="assistant", 
            content=output_text,
            figure_json=json.dumps(fig_json) if fig_json else None,
            analysis_code=raw_response
        )
        db.add(assistant_msg)
        db.commit()
            
        return {
            "chat_id": db_chat.id,
            "message_id": assistant_msg.id,
            "analysis": output_text,
            "figure": fig_json,
            "code": raw_response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/suggest-questions")
async def get_suggestions(
    user_id: str = Form(...), 
    api_key: str = Form(...),
    chat_id: Optional[int] = Form(None), # AÑADIDO
    data_source_id: Optional[int] = Form(None),
    provider: str = Form("gemini"),
    mistral_key: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    session_data = get_user_data(user_id, chat_id)
    
    # VALIDACIÓN DE FUENTE: Si el ID solicitado no coincide con lo cargado, forzar recarga
    if session_data and data_source_id and session_data.get("source_id") != data_source_id:
        session_data = None

    if not session_data and data_source_id:
        from src.database import DataSource
        from src.utils.common import load_source_to_session
        source = db.query(DataSource).filter(DataSource.id == data_source_id, DataSource.user_id == user_id).first()
        if source and load_source_to_session(user_id, source, chat_id):
            session_data = get_user_data(user_id, chat_id)

    if not session_data:
        raise HTTPException(status_code=404, detail="No hay datos cargados para generar sugerencias.")
    
    context = session_data["data"]
    if session_data["type"] == "sql":
        from src.connectors.data_connectors import get_db_schema
        context = get_db_schema(session_data["data"])

    suggestions = suggest_questions(context, api_key, mode=session_data["type"], provider=provider, mistral_key=mistral_key)
    return {"suggestions": suggestions}

@router.post("/detect-anomalies")
async def detect_anomalies():
    return {
        "analysis": "### 🚀 Detective de Datos: Próximamente\nEstamos refinando el motor de auditoría proactiva."
    }

@router.post("/generate-report-summary")
async def get_report_summary(
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
