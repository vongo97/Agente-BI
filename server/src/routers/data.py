import os
import shutil
import tempfile
import pandas as pd
import json
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from src.database import get_db, DataSource
from src.connectors.data_connectors import load_file_data, load_gsheets_data, get_sql_engine, get_db_schema
from src.utils.common import check_authorization, get_user_data, get_session_file, data_store, DATA_SOURCES_DIR, upload_file_to_cloud
from src.engine.bi_analyst import ai_data_cleaner

router = APIRouter(tags=["Data Management"])

@router.post("/upload")
async def upload_file(user_id: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    check_authorization(user_id)
    try:
        suffix = os.path.splitext(file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            file_location = tmp.name
        
        try:
            df = load_file_data(file_location)
            # Nombre de tabla limpio para Python/Pandas
            safe_filename = "".join([c if c.isalnum() else "_" for c in file.filename.split('.')[0]])
            
            # Obtener sesión existente o crear una nueva
            session_data = get_user_data(user_id)
            if not session_data or session_data.get("type") != "file":
                session_data = {"type": "file", "data": {}, "sources": []}
            
            # Añadir el nuevo DataFrame al diccionario
            session_data["data"][safe_filename] = df
            
            # Guardar DataSource en DB para el historial
            new_source = DataSource(
                user_id=user_id,
                name=file.filename,
                type="file",
                url="session_memory",
                columns=json.dumps(df.columns.tolist())
            )
            db.add(new_source)
            db.commit()
            db.refresh(new_source)
            
            session_data["sources"].append(new_source.id)
            data_store[user_id] = session_data
            
            # Persistencia en PKL (Pool acumulado)
            session_file = get_session_file(user_id)
            pd.to_pickle(session_data, session_file)
            
            return {
                "id": new_source.id,
                "filename": file.filename,
                "table_key": safe_filename,
                "columns": df.columns.tolist(),
                "rows": len(df),
                "total_tables": len(session_data["data"]),
                "message": f"Archivo '{file.filename}' añadido al pool de datos."
            }
        finally:
            if os.path.exists(file_location):
                os.remove(file_location)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error en /upload: {str(e)}")

@router.post("/connect-sql")
async def connect_sql(user_id: str = Form(...), url: str = Form(...), db: Session = Depends(get_db)):
    check_authorization(user_id)
    try:
        engine = get_sql_engine(url)
        schema = get_db_schema(engine)
        
        # Guardar en DB
        new_source = DataSource(user_id=user_id, name="SQL Connection", type="sql", url=url, columns=schema[:500])
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
        
        # SQL es especial, usualmente maneja sus propias tablas, 
        # pero lo marcamos como fuente activa
        data_store[user_id] = {"type": "sql", "data": engine, "schema": schema, "source_id": new_source.id}
        return {"message": "Conectado a SQL con éxito", "id": new_source.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error en conexión SQL: {str(e)}")

@router.post("/connect-gsheets")
async def connect_gsheets(user_id: str = Form(...), url: str = Form(...), db: Session = Depends(get_db)):
    check_authorization(user_id)
    try:
        df = load_gsheets_data(url)
        sheet_key = f"gsheet_{int(os.urandom(2).hex(), 16) % 1000}"
        
        session_data = get_user_data(user_id)
        if not session_data or session_data.get("type") != "file":
            session_data = {"type": "file", "data": {}, "sources": []}
            
        session_data["data"][sheet_key] = df
        
        new_source = DataSource(user_id=user_id, name="Google Sheet", type="gsheets", url=url, columns=json.dumps(df.columns.tolist()))
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
        
        session_data["sources"].append(new_source.id)
        data_store[user_id] = session_data
        pd.to_pickle(session_data, get_session_file(user_id))
        
        return {
            "id": new_source.id,
            "filename": "Google Sheet",
            "table_key": sheet_key,
            "columns": df.columns.tolist(),
            "total_tables": len(session_data["data"]),
            "message": "Hoja de Google añadida al pool."
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error en Google Sheets: {str(e)}")

@router.post("/clear-session")
async def clear_session(user_id: str = Form(...)):
    if user_id in data_store:
        del data_store[user_id]
    session_file = get_session_file(user_id)
    if os.path.exists(session_file):
        os.remove(session_file)
    return {"message": "Pool de datos limpiado."}

@router.post("/clean-data")
async def clean_data(
    user_id: str = Form(...), 
    api_key: str = Form(...),
    provider: str = Form("gemini"),
    mistral_key: Optional[str] = Form(None)
):
    check_authorization(user_id)
    session_data = get_user_data(user_id)
    if not session_data:
        raise HTTPException(status_code=400, detail="No hay datos cargados para limpiar.")
    
    if session_data["type"] != "file":
        raise HTTPException(status_code=400, detail="La limpieza automática solo está disponible para archivos y Google Sheets.")
    
    df = next(iter(session_data["data"].values()))
    cleaned_df, summary = ai_data_cleaner(df, api_key, provider, mistral_key)
    
    # Actualizar cache y persistencia
    session_data["data"][next(iter(session_data["data"].keys()))] = cleaned_df
    pd.to_pickle(session_data, get_session_file(user_id))
    
    from src.utils.common import json_serializable
    return json_serializable({
        "summary": summary,
        "columns": cleaned_df.columns.tolist(),
        "rows": len(cleaned_df)
    })

# --- GESTIÓN DE FUENTES GUARDADAS ---

@router.get("/data-sources")
async def get_data_sources(user_id: str, db: Session = Depends(get_db)):
    check_authorization(user_id)
    sources = db.query(DataSource).filter(DataSource.user_id == user_id).all()
    return sources

@router.post("/data-sources")
async def save_data_source(
    user_id: str = Form(...),
    name: str = Form(...),
    type: str = Form(...),
    url: str = Form(...),
    columns: Optional[str] = Form(None), # JSON string
    db: Session = Depends(get_db)
):
    check_authorization(user_id)
    new_source = DataSource(
        user_id=user_id,
        name=name,
        type=type,
        url=url,
        columns=columns
    )
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    return new_source

@router.delete("/data-sources/{source_id}")
async def delete_data_source(source_id: int, user_id: str, db: Session = Depends(get_db)):
    check_authorization(user_id)
    source = db.query(DataSource).filter(DataSource.id == source_id, DataSource.user_id == user_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")
    db.delete(source)
    db.commit()
    return {"message": "Fuente eliminada"}
