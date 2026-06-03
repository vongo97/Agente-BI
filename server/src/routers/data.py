import os
import shutil
import tempfile
import pandas as pd
import json
import hashlib
import logging
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from src.database import get_db, DataSource
from src.connectors.data_connectors import load_file_data, load_gsheets_data, get_sql_engine, get_db_schema
from src.utils.common import check_authorization, get_user_data, get_session_file, get_session_key, data_store, DATA_SOURCES_DIR, upload_file_to_cloud, get_authenticated_user
from src.engine.bi_analyst import ai_data_cleaner
from src.utils.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Data Management"])

# ── Cuotas por usuario ──────────────────────────────────────────────────────────────
_QUOTA_MAX_SOURCES   = 10              # Máx fuentes activas por usuario
_QUOTA_MAX_FILE_MB   = 25             # Máx por archivo (MB)
_QUOTA_MAX_TOTAL_MB  = 250            # Máx almacenamiento total por usuario (MB)

# MIME types permitidos directamente
_ALLOWED_MIME_TYPES = {
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel.sheet.macroEnabled.12",
}
# MIME fallback: octet-stream solo si la extensión es válida
_ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.xlsm'}


@router.post("/upload")
@limiter.limit("5/minute")
@limiter.limit("30/hour")
async def upload_file(request: Request, user_id: Optional[str] = Form(None), file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        authenticated_user = get_authenticated_user()
        check_authorization(authenticated_user)
        
        # 1. Sanitizar nombre de archivo
        clean_name = "".join([c if c.isalnum() or c in "._-" else "_" for c in file.filename])
        
        # Validar extensión
        _, ext = os.path.splitext(clean_name.lower())
        if ext not in _ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Extensión de archivo no permitida. Sube solo archivos CSV o Excel.")

        # Validar MIME type: permitido directo o octet-stream con extensión válida (fallback)
        content_type = (file.content_type or "").split(";")[0].strip().lower()
        if content_type not in _ALLOWED_MIME_TYPES:
            if ext in _ALLOWED_EXTENSIONS:
                # Fallback condicionado: aceptamos si la extensión es válida, dado que los browsers pueden enviar diferentes MIME types
                logger.debug("MIME %s aceptado por extensión válida: %s", content_type, ext)
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tipo de archivo no permitido (MIME: {content_type}). Sube solo archivos CSV o Excel."
                )

        # Validar tamaño de archivo (≤ 25 MB)
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)
        if file_size > _QUOTA_MAX_FILE_MB * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"El archivo excede el tamaño máximo permitido de {_QUOTA_MAX_FILE_MB}MB.")

        # Validar cuota: máx {_QUOTA_MAX_SOURCES} fuentes activas por usuario
        existing_count = db.query(DataSource).filter(DataSource.user_id == authenticated_user).count()
        if existing_count >= _QUOTA_MAX_SOURCES:
            raise HTTPException(
                status_code=400,
                detail=f"Límite alcanzado: máximo {_QUOTA_MAX_SOURCES} fuentes de datos por usuario. Elimina alguna antes de subir otra."
            )

        # Validar cuota de almacenamiento total (250 MB por usuario)
        user_sources = db.query(DataSource).filter(
            DataSource.user_id == authenticated_user,
            DataSource.type == "file"
        ).all()
        total_used_bytes = 0
        for src in user_sources:
            src_path = getattr(src, 'url', None)
            if src_path and os.path.exists(src_path):
                total_used_bytes += os.path.getsize(src_path)
        if total_used_bytes + file_size > _QUOTA_MAX_TOTAL_MB * 1024 * 1024:
            used_mb = total_used_bytes / (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"Cuota de almacenamiento superada ({used_mb:.1f} MB usados de {_QUOTA_MAX_TOTAL_MB} MB). Elimina archivos antes de continuar."
            )
            
        safe_user = hashlib.md5(authenticated_user.encode()).hexdigest()
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
        session_data = get_user_data(authenticated_user)
        if session_data is None or session_data.get("type") != "file":
            session_data = {"type": "file", "data": {}, "sources": []}
        
        session_data["data"][safe_filename] = df
        
        # 5. Guardar en Base de Datos
        new_source = DataSource(
            user_id=authenticated_user,
            name=file.filename,
            type="file",
            url=permanent_path,
            columns=json.dumps(df.columns.tolist())
        )
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
        
        session_data["sources"].append(new_source.id)
        data_store[f"{authenticated_user}_active"] = session_data
        
        # 6. Persistencia PKL
        session_file = get_session_file(authenticated_user)
        pd.to_pickle(session_data, session_file)
        
        # 7. Sincronización Nube (Opcional, no bloqueante ante errores de API)
        try:
            upload_file_to_cloud(permanent_path, f"data_sources/{permanent_name}")
            # También subimos el pkl de sesión para recuperarlo si el servidor se reinicia
            import os as _os
            upload_file_to_cloud(session_file, f"sessions/{_os.path.basename(session_file)}")
        except Exception:
            logger.warning("Nube: falló upload de %s (archivo guardado localmente).", permanent_name)

        return {
            "id": int(new_source.id),
            "filename": str(file.filename),
            "table_key": str(safe_filename),
            "columns": [str(c) for c in df.columns.tolist()],
            "rows": int(len(df)),
            "total_tables": int(len(session_data["data"])),
            "message": f"Archivo '{file.filename}' añadido con éxito."
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        is_render = os.getenv("RENDER", "false").lower() == "true"
        from src.utils.logging_config import safe_error_message
        clean_msg = safe_error_message(e)
        if not is_render:
            logger.exception("ERROR CRÍTICO /upload: %s", clean_msg)
        else:
            logger.error("ERROR CRÍTICO /upload: %s", clean_msg)
        raise HTTPException(status_code=500, detail="Error en el servidor al procesar el archivo. Por favor verifica que el formato sea válido.")

@router.post("/connect-sql")
@limiter.limit("5/minute")
@limiter.limit("30/hour")
async def connect_sql(request: Request, user_id: Optional[str] = Form(None), url: str = Form(...), db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    
    # Validar cuota de 10 fuentes
    existing_count = db.query(DataSource).filter(DataSource.user_id == authenticated_user).count()
    if existing_count >= _QUOTA_MAX_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Límite alcanzado: máximo {_QUOTA_MAX_SOURCES} fuentes de datos por usuario. Elimina alguna antes de agregar otra."
        )
        
    try:
        engine = get_sql_engine(url)
        schema = get_db_schema(engine)
        
        # Guardar en DB
        new_source = DataSource(user_id=authenticated_user, name="SQL Connection", type="sql", url=url, columns=schema[:500])
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
        
        data_store[get_session_key(authenticated_user)] = {"type": "sql", "data": engine, "schema": schema, "source_id": new_source.id}
        return {"message": "Conectado a SQL con éxito", "id": new_source.id}
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        clean_msg = safe_error_message(e)
        logger.error("Error en conexión SQL: %s", clean_msg)
        raise HTTPException(status_code=400, detail="Error en conexión SQL: No se pudo establecer la conexión. Por favor verifica los datos ingresados e intenta de nuevo.")

@router.post("/connect-gsheets")
@limiter.limit("5/minute")
@limiter.limit("30/hour")
async def connect_gsheets(request: Request, user_id: Optional[str] = Form(None), url: str = Form(...), db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    
    # Validar cuota de 10 fuentes
    existing_count = db.query(DataSource).filter(DataSource.user_id == authenticated_user).count()
    if existing_count >= _QUOTA_MAX_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Límite alcanzado: máximo {_QUOTA_MAX_SOURCES} fuentes de datos por usuario. Elimina alguna antes de agregar otra."
        )
        
    try:
        df = load_gsheets_data(url)
        if df is None or df.empty:
            raise HTTPException(status_code=400, detail="El Google Sheet parece estar vacío o no es público.")
            
        # Limitar celdas a un máximo de 1 millón para mitigar DoS
        MAX_CELLS = 1_000_000
        if df.size > MAX_CELLS:
            raise HTTPException(status_code=400, detail="El Google Sheet excede el tamaño máximo permitido de 1 millón de celdas.")
            
        sheet_key = f"gsheet_{int(os.urandom(2).hex(), 16) % 1000}"
        
        session_data = get_user_data(authenticated_user)
        if not session_data or session_data.get("type") != "file":
            session_data = {"type": "file", "data": {}, "sources": []}
            
        session_data["data"][sheet_key] = df
        
        new_source = DataSource(user_id=authenticated_user, name="Google Sheet", type="gsheets", url=url, columns=json.dumps(df.columns.tolist()))
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
        
        session_data["sources"].append(new_source.id)
        data_store[get_session_key(authenticated_user)] = session_data
        pd.to_pickle(session_data, get_session_file(authenticated_user))
        
        return {
            "id": new_source.id,
            "filename": "Google Sheet",
            "table_key": sheet_key,
            "columns": df.columns.tolist(),
            "total_tables": len(session_data["data"]),
            "message": "Hoja de Google añadida al pool."
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        clean_msg = safe_error_message(e)
        logger.error("Error en Google Sheets: %s", clean_msg)
        raise HTTPException(status_code=400, detail="Error en Google Sheets: No se pudo conectar u obtener datos del enlace. Asegúrate de que el documento sea público y contenga una estructura válida.")

@router.post("/clear-session")
@limiter.limit("10/minute")
async def clear_session(request: Request, user_id: Optional[str] = Form(None), db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    try:
        if authenticated_user in data_store:
            del data_store[authenticated_user]
        if f"{authenticated_user}_active" in data_store:
            del data_store[f"{authenticated_user}_active"]
            
        session_file = get_session_file(authenticated_user)
        if os.path.exists(session_file):
            os.remove(session_file)

        # Limpiar también los registros de data_sources de la base de datos para liberar la cuota
        sources = db.query(DataSource).filter(DataSource.user_id == authenticated_user).all()
        for source in sources:
            if source.type == "file" and source.url:
                try:
                    if os.path.exists(source.url):
                        os.remove(source.url)
                except Exception:
                    pass
        db.query(DataSource).filter(DataSource.user_id == authenticated_user).delete()
        db.commit()

        return {"message": "Pool de datos y fuentes limpiados."}
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("Error al limpiar sesión: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error interno al limpiar la sesión.")

@router.post("/remove-session-source")
@limiter.limit("10/minute")
async def remove_session_source(request: Request, user_id: Optional[str] = Form(None), source_id: int = Form(...), db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    try:
        session_data = get_user_data(authenticated_user)
        if not session_data:
            return {"message": "No hay sesión activa."}

        # 1. Quitar el ID de la lista de fuentes activas
        if "sources" in session_data and source_id in session_data["sources"]:
            session_data["sources"].remove(source_id)
        
        # 2. Limpiar el pool de datos actual para forzar recarga limpia
        session_data["data"] = {}
        
        # 3. Recargar solo las fuentes que quedaron
        from src.utils.common import load_source_to_session
        for sid in session_data.get("sources", []):
            source = db.query(DataSource).filter(DataSource.id == sid).first()
            if source:
                load_source_to_session(authenticated_user, source)
                
        return {"message": f"Fuente {source_id} eliminada de la sesión activa."}
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("Error al remover fuente: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error interno al remover la fuente de datos.")

@router.post("/clean-data")
@limiter.limit("5/minute")
async def clean_data(
    request: Request,
    user_id: Optional[str] = Form(None), 
    api_key: str = Form(...),
    provider: str = Form("gemini"),
    mistral_key: Optional[str] = Form(None)
):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    session_data = get_user_data(authenticated_user)
    if not session_data:
        raise HTTPException(status_code=400, detail="No hay datos cargados para limpiar.")
    
    if session_data["type"] != "file":
        raise HTTPException(status_code=400, detail="La limpieza automática solo está disponible para archivos y Google Sheets.")
    
    try:
        df = next(iter(session_data["data"].values()))
        cleaned_df, summary = ai_data_cleaner(df, api_key, provider, mistral_key)
        
        # Actualizar cache y persistencia
        session_data["data"][next(iter(session_data["data"].keys()))] = cleaned_df
        pd.to_pickle(session_data, get_session_file(authenticated_user))
        
        from src.utils.common import json_serializable
        return json_serializable({
            "summary": summary,
            "columns": cleaned_df.columns.tolist(),
            "rows": len(cleaned_df)
        })
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("Error al limpiar datos con IA: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error interno del servidor al limpiar datos.")

# --- GESTIÓN DE FUENTES GUARDADAS ---

@router.get("/data-sources")
@limiter.limit("15/minute")
async def get_data_sources(request: Request, user_id: Optional[str] = None, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    try:
        sources = db.query(DataSource).filter(DataSource.user_id == authenticated_user).all()
        return sources
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("Error al listar data-sources: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error interno al listar las fuentes.")

@router.post("/data-sources")
@limiter.limit("10/minute")
async def save_data_source(
    request: Request,
    user_id: Optional[str] = Form(None),
    name: str = Form(...),
    type: str = Form(...),
    url: str = Form(...),
    columns: Optional[str] = Form(None), # JSON string
    db: Session = Depends(get_db)
):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    
    # Validar cuota de 10 fuentes
    existing_count = db.query(DataSource).filter(DataSource.user_id == authenticated_user).count()
    if existing_count >= _QUOTA_MAX_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Límite alcanzado: máximo {_QUOTA_MAX_SOURCES} fuentes de datos por usuario. Elimina alguna antes de agregar otra."
        )
        
    try:
        new_source = DataSource(
            user_id=authenticated_user,
            name=name,
            type=type,
            url=url,
            columns=columns
        )
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
        return new_source
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("Error al guardar data-source: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error al guardar la fuente de datos.")

@router.delete("/data-sources/{source_id}")
@limiter.limit("10/minute")
async def delete_data_source(request: Request, source_id: int, user_id: Optional[str] = None, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    try:
        source = db.query(DataSource).filter(DataSource.id == source_id, DataSource.user_id == authenticated_user).first()
        if not source:
            raise HTTPException(status_code=404, detail="Fuente no encontrada")
        
        # Eliminar archivo físico si era de tipo 'file'
        if source.type == "file" and source.url:
            try:
                if os.path.exists(source.url):
                    os.remove(source.url)
                    logger.info("Archivo físico eliminado del disco: %s", source.url)
            except Exception as file_err:
                from src.utils.logging_config import safe_error_message
                logger.warning("No se pudo eliminar el archivo físico del disco: %s", safe_error_message(file_err))
                
        db.delete(source)
        db.commit()
        return {"message": "Fuente eliminada"}
    except HTTPException as he:
        raise he
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("Error al eliminar data-source: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error al eliminar la fuente de datos.")

@router.get("/sources")
@limiter.limit("15/minute")
async def list_data_sources(request: Request, user_id: Optional[str] = None, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    try:
        return db.query(DataSource).filter(DataSource.user_id == authenticated_user).order_by(DataSource.created_at.desc()).all()
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("Error al obtener sources: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error al obtener las fuentes de datos.")

@router.get("/sources/clear-force")
async def clear_force(db: Session = Depends(get_db)):
    from sqlalchemy import text
    try:
        db.execute(text("UPDATE chats SET data_source_id = NULL"))
        db.execute(text("UPDATE simulations SET data_source_id = NULL"))
        db.execute(text("DELETE FROM data_sources"))
        db.commit()
        return {"status": "success", "message": "Todas las fuentes de la base de datos local han sido eliminadas."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
