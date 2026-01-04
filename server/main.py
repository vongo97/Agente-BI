from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import pandas as pd
from dotenv import load_dotenv
from typing import List, Optional
import json

# Importar el motor de BI existente
from src.engine.bi_analyst import analyze_with_gemini, execute_analysis, validate_api_key
from src.connectors.data_connectors import load_file_data, load_gsheets_data, get_sql_engine, get_db_schema
from src.database import init_db, get_db, Chat, Message, DashboardItem
from src.utils.exporter import export_plotly_to_image, generate_pdf_report
from sqlalchemy.orm import Session
from fastapi import Depends, Response
from fastapi.responses import Response as FAResponse
import io

load_dotenv()

app = FastAPI(title="Agente BI API")

# Configurar CORS para el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*", # Permite todos los subdominios y dominios (necesario para Vercel dynamic URLs)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Almacenamiento temporal de datos (En un sistema real usaríamos una DB o Redis)
# Para este mvp, usaremos un diccionario en memoria por usuario
data_store = {}

def check_authorization(email: str):
    authorized_env = os.getenv("AUTHORIZED_EMAILS", "")
    if not authorized_env:
        return True # Si no hay lista, permitir todos (por ahora)
    authorized_list = [e.strip().lower() for e in authorized_env.split(",")]
    if email.lower() not in authorized_list:
        raise HTTPException(status_code=403, detail="Usuario no autorizado")
    return True

# Inicializar Base de Datos
init_db()

@app.get("/")
async def root():
    return {"status": "online", "message": "BI Agent API is running"}

@app.post("/validate-key")
async def validate_key(api_key: str = Form(...)):
    is_valid, error = validate_api_key(api_key)
    return {"valid": is_valid, "error": error}

@app.post("/upload")
async def upload_file(user_id: str = Form(...), file: UploadFile = File(...)):
    check_authorization(user_id)
    print(f"\n[DEBUG] RECIBIDO /upload - ID: '{user_id}' - File: {file.filename}")
    try:
        import tempfile
        suffix = os.path.splitext(file.filename)[1].lower()
        print(f"[DEBUG] Extensión detectada: {suffix}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            print(f"[DEBUG] Bytes leídos: {len(content)}")
            tmp.write(content)
            file_location = tmp.name
        
        print(f"[DEBUG] Guardado temporal en: {file_location}")
        
        try:
            print(f"[DEBUG] Cargando datos con load_file_data...")
            df = load_file_data(file_location)
            print(f"[DEBUG] Carga exitosa. Columnas: {df.columns.tolist()}")
            
            data_store[user_id] = {"type": "file", "data": df}
            
            return {
                "filename": file.filename,
                "columns": df.columns.tolist(),
                "rows": len(df),
                "message": "Archivo cargado con éxito"
            }
        finally:
            if os.path.exists(file_location):
                os.remove(file_location)
                print(f"[DEBUG] Archivo temporal eliminado")
                
    except Exception as e:
        import traceback
        error_detail = f"Error en /upload: {str(e)}"
        print(f"[DEBUG] {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(status_code=400, detail=error_detail)

@app.post("/connect-sql")
async def connect_sql(user_id: str = Form(...), url: str = Form(...)):
    check_authorization(user_id)
    try:
        engine = get_sql_engine(url)
        schema = get_db_schema(engine)
        
        data_store[user_id] = {"type": "sql", "data": engine, "schema": schema}
        
        return {"message": "Conectado a SQL con éxito", "schema_preview": schema[:200]}
    except Exception as e:
        import traceback
        print(f"Error en /connect-sql: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=400, detail=f"Error en conexión SQL: {str(e)}")

@app.post("/connect-gsheets")
async def connect_gsheets(user_id: str = Form(...), url: str = Form(...)):
    check_authorization(user_id)
    try:
        df = load_gsheets_data(url)
        if df is None:
            raise Exception("URL de Google Sheets no válida o no pública. Asegúrate de que el documento esté compartido como 'Cualquier persona con el enlace puede leer'.")
            
        data_store[user_id] = {"type": "file", "data": df}
        
        return {
            "filename": "Google Sheet",
            "columns": df.columns.tolist(),
            "rows": len(df),
            "message": "Google Sheet conectado con éxito"
        }
    except Exception as e:
        import traceback
        print(f"Error en /connect-gsheets: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=400, detail=f"Error en Google Sheets: {str(e)}")

@app.post("/analyze")
async def analyze(
    query: str = Form(...),
    api_key: str = Form(...),
    user_id: str = Form(...), # Email del usuario
    chat_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    check_authorization(user_id)
    if user_id not in data_store:
        raise HTTPException(status_code=400, detail="No hay datos cargados para analizar")
    
    session_data = data_store[user_id]
    
    try:
        # Determinar contexto según el modo
        if session_data["type"] == "file":
            context = session_data["data"]
            data_var = "df"
        else:
            context = session_data["schema"]
            data_var = "engine"

        # 1. Obtener código de Gemini (Pasando la API key del usuario)
        raw_response = analyze_with_gemini(context, query, api_key, mode=session_data["type"])
        
        # 2. Ejecutar análisis
        output_text, fig = execute_analysis(session_data["data"], raw_response, data_var)
        
        # Convertir figura de Plotly a JSON para el frontend
        fig_json = None
        if fig:
            fig_json = json.loads(fig.to_json())
            
        # --- PERSISTENCIA EN DB ---
        # 1. Buscar o crear el chat
        if chat_id:
            db_chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
        else:
            db_chat = Chat(user_id=user_id, title=query[:50] + "...")
            db.add(db_chat)
            db.commit()
            db.refresh(db_chat)
        
        # 2. Guardar mensaje del Usuario
        user_msg = Message(chat_id=db_chat.id, role="user", content=query)
        db.add(user_msg)
        
        # 3. Guardar respuesta del Asistente (incluyendo gráfico si existe)
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
        import traceback
        print(f"Error en /analyze: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-report-summary")
async def generate_summary(
    query: str = Form(...),
    api_key: str = Form(...),
    user_id: str = Form(...)
):
    check_authorization(user_id)
    if user_id not in data_store:
        raise HTTPException(status_code=400, detail="No hay datos cargados")
    
    session_data = data_store[user_id]
    summary = generate_report_narrative(session_data["data"], query, api_key, mode=session_data["type"])
    return {"summary": summary}

@app.post("/detect-anomalies")
async def detect_anomalies(
    api_key: str = Form(...),
    user_id: str = Form(...)
):
    check_authorization(user_id)
    print(f"\n[DEBUG] RECIBIDO /detect-anomalies - ID: '{user_id}'")
    print(f"[DEBUG] IDs en data_store: {list(data_store.keys())}")
    
    if user_id not in data_store:
        raise HTTPException(status_code=400, detail=f"No hay datos cargados para el usuario '{user_id}'. IDs activos: {list(data_store.keys())}")
    
    session_data = data_store[user_id]
    
    if session_data["type"] != "file":
         return {"analysis": "El detector proactivo actualmente solo está disponible para archivos (CSV/Excel). Próximamente soporte para SQL."}
    
    analysis = detect_anomalies_hybrid(session_data["data"], api_key)
    return {"analysis": analysis}

@app.get("/history")
async def get_history(user_id: str, db: Session = Depends(get_db)):
    check_authorization(user_id)
    chats = db.query(Chat).filter(Chat.user_id == user_id).order_by(Chat.created_at.desc()).all()
    return [{"id": c.id, "title": c.title, "created_at": c.created_at} for c in chats]

@app.get("/history/{chat_id}")
async def get_chat_details(chat_id: int, user_id: str, db: Session = Depends(get_db)):
    check_authorization(user_id)
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    
    messages = []
    for m in chat.messages:
        messages.append({
            "role": m.role,
            "content": m.content,
            "fig": json.loads(m.figure_json) if m.figure_json else None
        })
    return {"id": chat.id, "title": chat.title, "messages": messages}

# --- ENDPOINTS DE EXPORTACIÓN ---

@app.post("/export/chart")
async def export_chart(fig_json: dict):
    img_bytes = export_plotly_to_image(json.dumps(fig_json))
    if not img_bytes:
        raise HTTPException(status_code=500, detail="Error generando imagen del gráfico")
    
    filename = f"chart_{int(os.path.getmtime(__file__))}.png"
    return Response(
        content=img_bytes, 
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.post("/export/report")
async def export_pro_report(data: dict):
    user_id = data.get("user_id")
    check_authorization(user_id)
    
    title = data.get("title", "Reporte de Análisis BI")
    summary = data.get("summary", "Resumen ejecutivo no proporcionado.")
    items = data.get("items", [])
    
    pdf_bytes = generate_pro_report(title, summary, user_id, items)
    
    filename = f"reporte_ejecutivo_{int(os.path.getmtime(__file__))}.pdf"
    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/export/pdf/{chat_id}")
async def export_pdf_report(chat_id: int, user_id: str, db: Session = Depends(get_db)):
    check_authorization(user_id)
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    
    messages_list = []
    for m in chat.messages:
        messages_list.append({
            "role": m.role,
            "content": m.content,
            "fig": json.loads(m.figure_json) if m.figure_json else None
        })
    
    pdf_bytes = generate_pdf_report(user_id, messages_list)
    return Response(
        content=bytes(pdf_bytes), 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=reporte_bi_{chat_id}.pdf"}
    )

# --- ENDPOINTS DE DASHBOARD ---

@app.post("/dashboard/pin")
async def pin_to_dashboard(
    user_id: str = Form(...),
    chat_id: int = Form(...),
    message_id: int = Form(...),
    db: Session = Depends(get_db)
):
    check_authorization(user_id)
    # Verificar si ya existe
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

@app.get("/dashboard")
async def get_dashboard(user_id: str, db: Session = Depends(get_db)):
    check_authorization(user_id)
    items = db.query(DashboardItem).filter(DashboardItem.user_id == user_id).all()
    results = []
    for item in items:
        # Seguridad: Si el chat o mensaje original fueron eliminados, saltamos este item
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
        except Exception as e:
            print(f"Error procesando item del dashboard: {e}")
            continue
            
    return results

@app.delete("/dashboard/{item_id}")
async def unpin_from_dashboard(item_id: int, user_id: str, db: Session = Depends(get_db)):
    check_authorization(user_id)
    item = db.query(DashboardItem).filter(DashboardItem.id == item_id, DashboardItem.user_id == user_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    db.delete(item)
    db.commit()
    return {"message": "Eliminado del dashboard"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
