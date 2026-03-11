import os
import shutil
import tempfile
import pandas as pd
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from src.connectors.data_connectors import load_file_data, load_gsheets_data, get_sql_engine, get_db_schema
from src.utils.common import check_authorization, get_user_data, get_session_file, data_store
from src.engine.bi_analyst import ai_data_cleaner

router = APIRouter(tags=["Data Management"])

@router.post("/upload")
async def upload_file(user_id: str = Form(...), file: UploadFile = File(...)):
    check_authorization(user_id)
    try:
        suffix = os.path.splitext(file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            file_location = tmp.name
        
        try:
            df = load_file_data(file_location)
            session_data = get_user_data(user_id) or {"type": "file", "data": {}}
            safe_filename = "".join([c if c.isalnum() else "_" for c in file.filename.split('.')[0]])
            
            if session_data["type"] == "file":
                session_data["data"][safe_filename] = df
            else:
                session_data = {"type": "file", "data": {safe_filename: df}}
            
            data_store[user_id] = session_data
            pd.to_pickle(session_data, get_session_file(user_id))
            
            return {
                "filename": file.filename,
                "table_key": safe_filename,
                "columns": df.columns.tolist(),
                "rows": len(df),
                "total_tables": len(session_data["data"]),
                "message": f"Archivo '{file.filename}' añadido con éxito"
            }
        finally:
            if os.path.exists(file_location):
                os.remove(file_location)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=400, detail=f"Error en /upload: {str(e)}")

@router.post("/connect-sql")
async def connect_sql(user_id: str = Form(...), url: str = Form(...)):
    check_authorization(user_id)
    try:
        engine = get_sql_engine(url)
        schema = get_db_schema(engine)
        data_store[user_id] = {"type": "sql", "data": engine, "schema": schema}
        return {"message": "Conectado a SQL con éxito", "schema_preview": schema[:200]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error en conexión SQL: {str(e)}")

@router.post("/connect-gsheets")
async def connect_gsheets(user_id: str = Form(...), url: str = Form(...)):
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
            
        data_store[user_id] = session_data
        pd.to_pickle(session_data, get_session_file(user_id))
        
        return {
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
async def clean_data(user_id: str = Form(...), api_key: str = Form(...)):
    check_authorization(user_id)
    session_data = get_user_data(user_id)
    if not session_data:
        raise HTTPException(status_code=400, detail="No hay datos cargados para limpiar.")
    
    if session_data["type"] != "file":
        raise HTTPException(status_code=400, detail="La limpieza automática solo está disponible para archivos y Google Sheets.")
    
    df = next(iter(session_data["data"].values()))
    cleaned_df, summary = ai_data_cleaner(df, api_key)
    
    # Actualizar cache y persistencia
    session_data["data"][next(iter(session_data["data"].keys()))] = cleaned_df
    pd.to_pickle(session_data, get_session_file(user_id))
    
    return {
        "summary": summary,
        "columns": cleaned_df.columns.tolist(),
        "rows": len(cleaned_df)
    }
