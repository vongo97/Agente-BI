import os
import pandas as pd
import json
import hashlib
import logging
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from src.database import get_db, DataSource, UserConfig
from src.connectors.data_connectors import load_gsheets_data, get_sql_engine, get_db_schema
from src.utils.common import check_authorization, get_user_data, get_session_file, get_session_key, data_store, DATA_SOURCES_DIR, get_authenticated_user, save_user_data, ensure_user_session
from src.services.storage_service import upload_bytes, delete_object, is_cloud_key
from src.engine.bi_analyst import ai_data_cleaner
from src.utils.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Data Management"])

# â”€â”€ Cuotas por usuario â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_QUOTA_MAX_SOURCES   = 100             # MÃ¡x fuentes activas por usuario
_QUOTA_MAX_FILE_MB   = 25             # MÃ¡x por archivo (MB)
_QUOTA_MAX_TOTAL_MB  = 250            # MÃ¡x almacenamiento total por usuario (MB)

# MIME types permitidos directamente
_ALLOWED_MIME_TYPES = {
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel.sheet.macroEnabled.12",
}
# MIME fallback: octet-stream solo si la extensiÃ³n es vÃ¡lida
_ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.xlsm'}


@router.post("/upload")
@limiter.limit("5/minute")
@limiter.limit("30/hour")
async def upload_file(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        authenticated_user = get_authenticated_user()
        check_authorization(authenticated_user)
        
        # 1. Validar path traversal en el nombre original
        raw_name = file.filename or ""
        if ".." in raw_name or "/" in raw_name or "\\" in raw_name:
            logger.warning("SECURITY_REJECTED path_traversal filename='%s' user=%s", raw_name, authenticated_user)
            raise HTTPException(status_code=400, detail="Nombre de archivo invÃ¡lido.")

        # Sanitizar nombre de archivo
        clean_name = "".join([c if c.isalnum() or c in "._-" else "_" for c in raw_name])

        # Validar extensiÃ³n
        _, ext = os.path.splitext(clean_name.lower())
        if ext not in _ALLOWED_EXTENSIONS:
            logger.warning("SECURITY_REJECTED invalid_extension filename='%s' ext='%s' user=%s", raw_name, ext, authenticated_user)
            raise HTTPException(status_code=400, detail="ExtensiÃ³n de archivo no permitida. Sube solo archivos CSV o Excel.")

        # Validar MIME type: permitido directo o octet-stream con extensiÃ³n vÃ¡lida (fallback)
        content_type = (file.content_type or "").split(";")[0].strip().lower()
        if content_type not in _ALLOWED_MIME_TYPES:
            if ext in _ALLOWED_EXTENSIONS:
                logger.debug("MIME %s aceptado por extensiÃ³n vÃ¡lida: %s", content_type, ext)
            else:
                logger.warning("SECURITY_REJECTED invalid_mime filename='%s' mime='%s' ext='%s' user=%s", raw_name, content_type, ext, authenticated_user)
                raise HTTPException(
                    status_code=400,
                    detail=f"Tipo de archivo no permitido (MIME: {content_type}). Sube solo archivos CSV o Excel."
                )

        # Validar tamaÃ±o de archivo (â‰¤ 25 MB)
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)
        if file_size > _QUOTA_MAX_FILE_MB * 1024 * 1024:
            size_mb = file_size / (1024 * 1024)
            logger.warning("SECURITY_REJECTED file_too_large filename='%s' size_mb=%.2f limit_mb=%d user=%s", raw_name, size_mb, _QUOTA_MAX_FILE_MB, authenticated_user)
            raise HTTPException(status_code=400, detail=f"El archivo excede el tamaÃ±o mÃ¡ximo permitido de {_QUOTA_MAX_FILE_MB}MB.")

        # Validar cuota: mÃ¡x {_QUOTA_MAX_SOURCES} fuentes activas por usuario
        existing_count = db.query(DataSource).filter(DataSource.user_id == authenticated_user).count()
        if existing_count >= _QUOTA_MAX_SOURCES:
            raise HTTPException(
                status_code=400,
                detail=f"LÃ­mite alcanzado: mÃ¡ximo {_QUOTA_MAX_SOURCES} fuentes de datos por usuario. Elimina alguna antes de subir otra."
            )

        # Validar cuota de almacenamiento total (250 MB por usuario)
        user_sources = db.query(DataSource).filter(
            DataSource.user_id == authenticated_user,
            DataSource.type == "file"
        ).all()
        total_used_bytes = 0
        for src in user_sources:
            # Cuota por tamaÃ±o registrado en DB: independiente del disco efÃ­mero
            # (con claves de nube en url ya no hay archivo local que medir).
            total_used_bytes += getattr(src, 'size_bytes', None) or 0
        if total_used_bytes + file_size > _QUOTA_MAX_TOTAL_MB * 1024 * 1024:
            used_mb = total_used_bytes / (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"Cuota de almacenamiento superada ({used_mb:.1f} MB usados de {_QUOTA_MAX_TOTAL_MB} MB). Elimina archivos antes de continuar."
            )
            
        safe_user = hashlib.md5(authenticated_user.encode()).hexdigest()
        permanent_name = f"{safe_user}_{int(datetime.utcnow().timestamp())}_{clean_name}"
        permanent_path = os.path.join(DATA_SOURCES_DIR, permanent_name)

        # â”€â”€ LEER ARCHIVO EN MEMORIA â”€â”€
        file.file.seek(0)
        raw_bytes = file.file.read()

        # â”€â”€ PARSEAR DESDE BYTES EN MEMORIA â”€â”€
        from src.connectors.data_connectors import ArchivoInvalido, load_file_data_from_bytes
        try:
            df = load_file_data_from_bytes(raw_bytes, clean_name)
        except ArchivoInvalido as inv:
            logger.info("UPLOAD_REJECTED motivo=archivo_invalido file=%s user=%s", clean_name, authenticated_user)
            raise HTTPException(status_code=400, detail=str(inv))
        except HTTPException:
            raise
        except Exception:
            logger.exception("Fallo no controlado parseando %s", clean_name)
            raise HTTPException(
                status_code=400,
                detail="No pudimos leer el archivo. Verifica que sea un CSV o Excel vÃ¡lido.",
            )

        safe_filename = "".join([c if c.isalnum() else "_" for c in clean_name.split('.')[0]])

        # ── ESCRIBIR ARCHIVO AL DISCO ──
        try:
            with open(permanent_path, 'wb') as f:
                f.write(raw_bytes)
        except Exception as e:
            logger.error("No se pudo escribir el archivo %s (tipo=%s)", permanent_name, type(e).__name__)
            try:
                if os.path.exists(permanent_path): os.remove(permanent_path)
            except Exception:
                pass
            raise HTTPException(
                status_code=500,
                detail="Error interno al guardar el archivo. Inténtalo de nuevo más tarde."
            )

        # ── SUBIR A LA NUBE (opcional: si falla, el archivo queda en disco local) ──
        cloud_key = f"data_sources/{safe_user}/{permanent_name}"
        cloud_ok = False
        try:
            cloud_ok = upload_bytes(cloud_key, raw_bytes)
        except Exception:
            logger.warning("Subida a la nube falló para %s; el archivo queda solo en disco local", permanent_name)
        # El archivo queda ademÃ¡s como cachÃ© local (permanent_path) para
        # accesos inmediatos; la verdad fuente es el objeto en la nube.

        return {
            "id": int(new_source.id),
            "filename": str(file.filename),
            "table_key": str(safe_filename),
            "columns": [str(c) for c in df.columns.tolist()],
            "rows": int(len(df)),
            "total_tables": int(len(session_data["data"])),
            "persisted": True,
            "message": f"Archivo '{file.filename}' aÃ±adido con Ã©xito y persistido en la nube."
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        is_render = os.getenv("RENDER", "false").lower() == "true"
        from src.utils.logging_config import safe_error_message
        clean_msg = safe_error_message(e)
        if not is_render:
            logger.exception("ERROR CRÃTICO /upload: %s", clean_msg)
        else:
            logger.error("ERROR CRÃTICO /upload: %s", clean_msg)
        raise HTTPException(status_code=500, detail="Error en el servidor al procesar el archivo. Por favor verifica que el formato sea vÃ¡lido.")

@router.post("/connect-sql")
@limiter.limit("5/minute")
@limiter.limit("30/hour")
async def connect_sql(request: Request, url: str = Form(...), db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    
    # ValidaciÃ³n SSRF: rechazar hosts locales/privados/no permitidos ANTES de conectar
    from src.utils.security import validate_external_url_host
    try:
        validate_external_url_host(url)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"ConexiÃ³n rechazada por seguridad: {ve}")
    
    # Validar cuota de 10 fuentes
    existing_count = db.query(DataSource).filter(DataSource.user_id == authenticated_user).count()
    if existing_count >= _QUOTA_MAX_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"LÃ­mite alcanzado: mÃ¡ximo {_QUOTA_MAX_SOURCES} fuentes de datos por usuario. Elimina alguna antes de agregar otra."
        )
        
    try:
        engine = get_sql_engine(url)
        schema = get_db_schema(engine)
        
        # Guardar en DB (URL cifrada en reposo: contiene credenciales)
        from src.utils.security import encrypt_key
        encrypted_url = encrypt_key(url)
        new_source = DataSource(user_id=authenticated_user, name="SQL Connection", type="sql", url=encrypted_url, columns=schema[:500])
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
        
        data_store[get_session_key(authenticated_user)] = {"type": "sql", "data": engine, "schema": schema, "source_id": new_source.id}
        return {"message": "Conectado a SQL con Ã©xito", "id": new_source.id}
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        clean_msg = safe_error_message(e)
        logger.error("Error en conexiÃ³n SQL: %s", clean_msg)
        raise HTTPException(status_code=400, detail="Error en conexiÃ³n SQL: No se pudo establecer la conexiÃ³n. Por favor verifica los datos ingresados e intenta de nuevo.")

@router.post("/connect-gsheets")
@limiter.limit("5/minute")
@limiter.limit("30/hour")
async def connect_gsheets(request: Request, url: str = Form(...), db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    
    # Validar cuota de 10 fuentes
    existing_count = db.query(DataSource).filter(DataSource.user_id == authenticated_user).count()
    if existing_count >= _QUOTA_MAX_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"LÃ­mite alcanzado: mÃ¡ximo {_QUOTA_MAX_SOURCES} fuentes de datos por usuario. Elimina alguna antes de agregar otra."
        )
        
    try:
        df = load_gsheets_data(url)
        if df is None or df.empty:
            raise HTTPException(status_code=400, detail="El Google Sheet parece estar vacÃ­o o no es pÃºblico.")
            
        # Limitar celdas a un mÃ¡ximo de 1 millÃ³n para mitigar DoS
        MAX_CELLS = 1_000_000
        if df.size > MAX_CELLS:
            raise HTTPException(status_code=400, detail="El Google Sheet excede el tamaÃ±o mÃ¡ximo permitido de 1 millÃ³n de celdas.")
            
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
        save_user_data(authenticated_user, session_data)
        
        return {
            "id": new_source.id,
            "filename": "Google Sheet",
            "table_key": sheet_key,
            "columns": df.columns.tolist(),
            "total_tables": len(session_data["data"]),
            "message": "Hoja de Google aÃ±adida al pool."
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        clean_msg = safe_error_message(e)
        logger.error("Error en Google Sheets: %s", clean_msg)
        raise HTTPException(status_code=400, detail="Error en Google Sheets: No se pudo conectar u obtener datos del enlace. AsegÃºrate de que el documento sea pÃºblico y contenga una estructura vÃ¡lida.")

@router.post("/clear-session")
@limiter.limit("10/minute")
async def clear_session(request: Request, db: Session = Depends(get_db)):
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

        # Limpiar tambiÃ©n los registros de data_sources de la base de datos para liberar la cuota
        sources = db.query(DataSource).filter(DataSource.user_id == authenticated_user).all()
        for source in sources:
            if source.type == "file" and source.url:
                if is_cloud_key(source.url):
                    delete_object(source.url)
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
        logger.error("Error al limpiar sesiÃ³n: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error interno al limpiar la sesiÃ³n.")

@router.post("/remove-session-source")
@limiter.limit("10/minute")
async def remove_session_source(request: Request, source_id: int = Form(...), db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    try:
        session_data = ensure_user_session(authenticated_user, db)
        if not session_data:
            return {"message": "No hay sesiÃ³n activa."}

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
                
        return {"message": f"Fuente {source_id} eliminada de la sesiÃ³n activa."}
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("Error al remover fuente: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error interno al remover la fuente de datos.")

@router.post("/clean-data")
@limiter.limit("5/minute")
async def clean_data(
    request: Request,
    api_key: str = Form(...),
    provider: str = Form("gemini"),
    mistral_key: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    
    # Cargar configuraciÃ³n una vez
    user_config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
    
    # --- AUTO-RECUPERACIÃ“N DE LLAVES CIFRADAS (P-04: solo la clave del proveedor activo) ---
    from src.engine.providers import resolve_keys
    api_key, mistral_key, key_error = resolve_keys(provider, api_key, mistral_key, user_config)
    if key_error and provider != "hybrid":
        raise HTTPException(status_code=400, detail=key_error)
            
    # Validar que las llaves descifradas no sean vacÃ­as o None si el proveedor las requiere
    if provider == "gemini" and not api_key:
        raise HTTPException(status_code=400, detail="Clave API de Gemini no vÃ¡lida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
    elif provider == "mistral" and not mistral_key:
        raise HTTPException(status_code=400, detail="Clave API de Mistral no vÃ¡lida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
    elif provider == "groq" and not api_key:
        raise HTTPException(status_code=400, detail="Clave API de Groq no vÃ¡lida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")

    session_data = ensure_user_session(authenticated_user, db)
    if not session_data:
        raise HTTPException(status_code=400, detail="No hay datos cargados para limpiar.")
    
    if session_data["type"] != "file":
        raise HTTPException(status_code=400, detail="La limpieza automÃ¡tica solo estÃ¡ disponible para archivos y Google Sheets.")
    
    try:
        df = next(iter(session_data["data"].values()))
        
        # Recuperar estrategia de limpieza personalizada del usuario
        strategy = user_config.magic_clean_strategy if user_config and user_config.magic_clean_strategy else "remove"
        
        cleaned_df, summary = ai_data_cleaner(df, api_key, provider, mistral_key, strategy=strategy)
        
        # Actualizar cache y persistencia
        session_data["data"][next(iter(session_data["data"].keys()))] = cleaned_df
        data_store[get_session_key(authenticated_user)] = session_data
        save_user_data(authenticated_user, session_data)
        
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

# --- GESTIÃ“N DE FUENTES GUARDADAS ---

@router.get("/data-sources")
@limiter.limit("15/minute")
async def get_data_sources(request: Request, db: Session = Depends(get_db)):
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
            detail=f"LÃ­mite alcanzado: mÃ¡ximo {_QUOTA_MAX_SOURCES} fuentes de datos por usuario. Elimina alguna antes de agregar otra."
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
async def delete_data_source(request: Request, source_id: int, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    try:
        source = db.query(DataSource).filter(DataSource.id == source_id, DataSource.user_id == authenticated_user).first()
        if not source:
            raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")
        
        # Eliminar de la nube (fuente de verdad) y del disco si era de tipo 'file'
        if source.type == "file" and source.url:
            if is_cloud_key(source.url):
                delete_object(source.url)
            try:
                if os.path.exists(source.url):
                    os.remove(source.url)
                    logger.info("Archivo fÃ­sico eliminado del disco: %s", source.url)
            except Exception as file_err:
                from src.utils.logging_config import safe_error_message
                logger.warning("No se pudo eliminar el archivo fÃ­sico del disco: %s", safe_error_message(file_err))
                
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
async def list_data_sources(request: Request, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    try:
        return db.query(DataSource).filter(DataSource.user_id == authenticated_user).order_by(DataSource.created_at.desc()).all()
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("Error al obtener sources: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error al obtener las fuentes de datos.")

# NOTA DE SEGURIDAD: el endpoint global /sources/clear-force fue eliminado (auditorÃ­a 2026-02).
# Borraba TODA la tabla data_sources sin filtro por usuario bajo ciertos entornos.
# Para depuraciÃ³n local, usa el borrado por fuente existente (DELETE /sources/{id}).
