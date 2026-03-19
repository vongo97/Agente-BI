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
from src.utils.common import check_authorization, get_user_data, get_session_file, data_store, DATA_SOURCES_DIR
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
            safe_filename = "".join([c if c.isalnum() else "_" for c in file.filename.split('.')[0]])
            # 1. Crear DataSource primero para obtener el ID
            new_source = DataSource(
                user_id=user_id,
                name=file.filename,
                type="file",
                url="pending", # Se actualizará después
                columns=json.dumps(df.columns.tolist())
            )
            db.add(new_source)
            db.commit()
            db.refresh(new_source)

            # 2. Guardar el archivo PKL ÚNICO para esta fuente
            unique_pkl = get_session_file(user_id, new_source.id)
            session_data = {"type": "file", "data": {safe_filename: df}, "source_id": new_source.id}
            pd.to_pickle(session_data, unique_pkl)
            
            # 3. Actualizar URL y sesión activa
            new_source.url = unique_pkl
            db.commit()
            
            data_store[user_id] = session_data
            
            return {
                "id": new_source.id,
                "filename": file.filename,
                "table_key": safe_filename,
                "columns": df.columns.tolist(),
                "rows": len(df),
                "total_tables": 1,
                "message": f"Archivo '{file.filename}' procesado con identidad única (ID: {new_source.id})"
            }
        finally:
            if os.path.exists(file_location):
                os.remove(file_location)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=400, detail=f"Error en /upload: {str(e)}")

@router.post("/connect-sql")
async def connect_sql(user_id: str = Form(...), url: str = Form(...), db: Session = Depends(get_db)):
    check_authorization(user_id)
    try:
        engine = get_sql_engine(url)
        schema = get_db_schema(engine)
        
        # Guardar en DB para persistencia
        new_source = DataSource(user_id=user_id, name="SQL Connection", type="sql", url=url, columns=schema[:500])
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
        
        data_store[user_id] = {"type": "sql", "data": engine, "schema": schema, "source_id": new_source.id}
        return {"message": "Conectado a SQL con éxito", "id": new_source.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error en conexión SQL: {str(e)}")

@router.post("/connect-gsheets")
async def connect_gsheets(user_id: str = Form(...), url: str = Form(...), db: Session = Depends(get_db)):
    check_authorization(user_id)
    try:
        df = load_gsheets_data(url)
        if df is None:
            raise Exception("URL de Google Sheets no válida o no pública.")
            
        session_data = get_user_data(user_id) or {"type": "file", "data": {}}
        sheet_key = f"gsheet_{len(session_data.get('data', {})) + 1}"
        
        if session_data["type"] == "file":
            session_data["data"][sheet_key] = df
        else:
            session_data = {"type": "file", "data": {sheet_key: df}}
            
        # Guardar en DB
        new_source = DataSource(user_id=user_id, name="Google Sheet", type="gsheets", url=url, columns=json.dumps(df.columns.tolist()))
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
            
        # 3. Crear sesión LIMPIA para esta fuente de GSheet
        session_data = {"type": "file", "data": {sheet_key: df}, "source_id": new_source.id}
        data_store[user_id] = session_data
        pd.to_pickle(session_data, get_session_file(user_id, new_source.id))
        
        # 4. Actualizar URL de la fuente (usamos el mismo pkl para consistencia)
        new_source.url = get_session_file(user_id, new_source.id)
        db.commit()
        
        return {
            "id": new_source.id,
            "filename": "Google Sheet",
            "table_key": sheet_key,
            "columns": df.columns.tolist(),
            "rows": len(df),
            "total_tables": len(session_data["data"]),
            "message": "Google Sheet conectado con éxito"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error en Google Sheets: {str(e)}")

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
    
    return {
        "summary": summary,
        "columns": cleaned_df.columns.tolist(),
        "rows": len(cleaned_df)
    }

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
