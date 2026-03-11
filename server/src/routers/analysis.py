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

    session_data = get_user_data(user_id)
    if not session_data:
        raise HTTPException(status_code=400, detail="No hay datos cargados para analizar.")
    
    try:
        data_var = "dfs" if session_data["type"] == "file" else "engine"
        
        # 1. Obtener código de la IA
        raw_response = analyze_data(session_data["data"], query, api_key, mode=session_data["type"], provider=provider, mistral_key=mistral_key)
        
        # 2. Ejecutar análisis final
        output_text, fig = execute_analysis(session_data["data"], raw_response, data_var)
        
        fig_json = json.loads(fig.to_json()) if fig else None
            
        # Persistencia
        if chat_id:
            db_chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
        else:
            db_chat = Chat(user_id=user_id, title=query[:50] + "...")
            db.add(db_chat)
            db.commit()
            db.refresh(db_chat)
        
        user_msg = Message(chat_id=db_chat.id, role="user", content=query)
        db.add(user_msg)
        
        assistant_msg = Message(
            chat_id=db_chat.id, 
            role="assistant", 
            content=output_text,
            figure_json=json.dumps(fig_json) if fig_json else None
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
    provider: str = Form("gemini"),
    mistral_key: Optional[str] = Form(None)
):
    session_data = get_user_data(user_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="No hay datos cargados.")
    
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
