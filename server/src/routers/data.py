import os
import shutil
import tempfile
import pandas as pd
import json
import hashlib
from datetime import datetime
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
    try:
        check_authorization(user_id)
        
        # 1. Sanitizar nombre de archivo (Evitar problemas en Windows)
        clean_name = "".join([c if c.isalnum() or c in "._-" else "_" for c in file.filename])
        safe_user = hashlib.md5(user_id.encode()).hexdigest()
        permanent_name = f"{safe_user}_{int(datetime.utcnow().timestamp())}_{clean_name}"
        permanent_path = os.path.join(DATA_SOURCES_DIR, permanent_name)
        
        # 2. Guardar archivo físico
        file.file.seek(0)
        with open(permanent_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 3. Procesar datos
        df = load_file_data(permanent_path)
        safe_filename = "".join([c if c.isalnum() else "_" for c in clean_name.split('.')[0]])
        
        # 4. Actualizar sesión en memoria
        session_data = get_user_data(user_id)
        if session_data is None or session_data.get("type") != "file":
            session_data = {"type": "file", "data": {}, "sources": []}
        
        session_data["data"][safe_filename] = df
        
        # 5. Guardar en Base de Datos
        new_source = DataSource(
            user_id=user_id,
            name=file.filename,
            type="file",
            url=permanent_path,
            columns=json.dumps(df.columns.tolist())
        )
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
        
        session_data["sources"].append(new_source.id)
        data_store[f"{user_id}_active"] = session_data
        
        # 6. Persistencia PKL
        session_file = get_session_file(user_id)
        pd.to_pickle(session_data, session_file)
        
        # 7. Sincronización Nube (Opcional, no bloqueante ante errores de API)
        try:
            upload_file_to_cloud(permanent_path, f"data_sources/{permanent_name}")
        except:
            print(f"AVISO: Falló la subida a la nube para {permanent_name} (pero el archivo se guardó localmente)")

        return {
            "id": int(new_source.id),
            "filename": str(file.filename),
            "table_key": str(safe_filename),
            "columns": [str(c) for c in df.columns.tolist()],
            "rows": int(len(df)),
            "total_tables": int(len(session_data["data"])),
            "message": f"Archivo '{file.filename}' añadido con éxito."
        }
        
    except Exception as e:
        import traceback
        print(f"!!! ERROR CRÍTICO EN /UPLOAD: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error en el servidor al procesar el archivo: {str(e)}")

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

@router.get("/sources")
async def list_data_sources(user_id: str, db: Session = Depends(get_db)):
    return db.query(DataSource).filter(DataSource.user_id == user_id).order_by(DataSource.created_at.desc()).all()
