from fastapi import APIRouter, Body, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
import json
import logging
from src.database import get_db, Chat, Message, DashboardItem, DataSource
from src.engine.bi_analyst import generate_auto_dashboard
from src.engine.executor import execute_analysis, execute_sql_with_params
from src.engine.insight_auditor import AUDIT_MARKER
from src.utils.common import check_authorization, get_user_data, get_authenticated_user, ensure_user_session
from src.utils.limiter import limiter
from src.utils.logging_config import log_ignored_error
import pandas as pd

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Dashboard"])


def _serialize_chat_source(source: DataSource) -> dict:
    return {
        "id": source.id,
        "name": source.name,
        "type": source.type,
        "columns": json.loads(source.columns) if source.columns else [],
    }

@router.get("/history")
async def get_history(db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    chats = db.query(Chat).filter(Chat.user_id == authenticated_user).order_by(desc(Chat.created_at)).all()
    return [{"id": c.id, "title": c.title, "created_at": c.created_at} for c in chats]

@router.get("/history/{chat_id}")
async def get_chat_details(chat_id: int, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == authenticated_user).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")
    
    messages = []
    for m in chat.messages:
        audit_payload = None
        if m.analysis_code and m.analysis_code.startswith(AUDIT_MARKER):
            try:
                audit_payload = json.loads(m.analysis_code[len(AUDIT_MARKER):])
            except (TypeError, ValueError):
                logger.warning("Auditoría persistida con payload inválido en mensaje %s", m.id)
        messages.append({
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "fig": json.loads(m.figure_json) if m.figure_json else None,
            "audit": audit_payload,
        })
    
    chat_sources = list(chat.data_sources or [])
    if not chat_sources and chat.data_source:
        chat_sources = [chat.data_source]
    source_infos = [_serialize_chat_source(source) for source in chat_sources]

    return {
        "id": chat.id, 
        "title": chat.title, 
        "messages": messages,
        "data_sources": source_infos,
        "data_source": source_infos[0] if source_infos else None,
    }


@router.put("/history/{chat_id}/sources")
@limiter.limit("30/minute")
async def set_chat_sources(
    request: Request,
    chat_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    """Replace the file sources attached to an owned chat and rebuild its pool."""
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    chat = db.query(Chat).filter(
        Chat.id == chat_id, Chat.user_id == authenticated_user
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")

    raw_ids = payload.get("source_ids") if isinstance(payload, dict) else None
    if not isinstance(raw_ids, list) or not all(type(item) is int for item in raw_ids):
        raise HTTPException(status_code=400, detail="source_ids debe ser una lista de identificadores.")
    source_ids = list(dict.fromkeys(raw_ids))

    sources = db.query(DataSource).filter(
        DataSource.user_id == authenticated_user,
        DataSource.id.in_(source_ids),
    ).all() if source_ids else []
    if len(sources) != len(source_ids):
        raise HTTPException(status_code=404, detail="Una o más fuentes no existen o no son accesibles.")
    if any(source.type != "file" for source in sources):
        raise HTTPException(status_code=400, detail="Por ahora, los chats multiarchivo admiten archivos CSV/Excel.")

    source_order = {source_id: index for index, source_id in enumerate(source_ids)}
    sources.sort(key=lambda source: source_order[int(source.id)])
    chat.data_sources = sources
    chat.data_source_id = sources[0].id
    db.commit()

    session_data = ensure_user_session(authenticated_user, db, chat_id)
    if source_ids and (not session_data or len(session_data.get("sources", [])) != len(source_ids)):
        raise HTTPException(
            status_code=400,
            detail="No se pudieron cargar todas las fuentes vinculadas a la conversación.",
        )
    return {"data_sources": [_serialize_chat_source(source) for source in sources]}

@router.post("/dashboard/pin")
async def pin_to_dashboard(
    chat_id: int = Form(...),
    message_id: int = Form(...),
    db: Session = Depends(get_db)
):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == authenticated_user).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")
        
    message = db.query(Message).filter(Message.id == message_id, Message.chat_id == chat_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")

    existing = db.query(DashboardItem).filter(
        DashboardItem.user_id == authenticated_user, 
        DashboardItem.message_id == message_id
    ).first()
    
    if existing:
        return {"message": "Ya está en el dashboard"}
    
    new_item = DashboardItem(user_id=authenticated_user, chat_id=chat_id, message_id=message_id)
    db.add(new_item)
    db.commit()
    return {"message": "Anclado al dashboard con éxito"}

@router.get("/dashboard")
async def get_dashboard(db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    items = db.query(DashboardItem).filter(DashboardItem.user_id == authenticated_user).all()
    results = []
    for item in items:
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
        except Exception as exc:
            # P-36: un item del dashboard con `figure_json` corrupto no puede
            # romper la carga de los demás. Se salta ese item, pero se registra
            # cuál fue para poder repararlo (antes el fallo era invisible).
            log_ignored_error(
                logger,
                "serialización de un item del dashboard",
                exc,
                level=logging.WARNING,
                item_id=item.id,
            )
            continue
    return results

@router.delete("/dashboard/{item_id}")
@limiter.limit("15/minute")
async def unpin_from_dashboard(request: Request, item_id: int, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    try:
        item = db.query(DashboardItem).filter(DashboardItem.id == item_id, DashboardItem.user_id == authenticated_user).first()
        if not item:
            raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")
        db.delete(item)
        db.commit()
        return {"message": "Eliminado del dashboard"}
    except HTTPException as he:
        raise he
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("Error al desanclar del dashboard: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error interno al desanclar el elemento.")

@router.post("/auto-dashboard")
@limiter.limit("5/minute")
@limiter.limit("20/hour")
async def auto_dashboard(
    request: Request,
    api_key: Optional[str] = Form(None),
    data_source_id: Optional[int] = Form(None),
    provider: str = Form("gemini"),
    mistral_key: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    from src.utils.common import ensure_user_session
    session_data = ensure_user_session(authenticated_user, db)
    
    if not session_data:
         raise HTTPException(status_code=400, detail="Se requieren datos activos (SQL o Archivo) para generar un Auto-Dashboard.")
         
    # --- AUTO-RECUPERACIÓN DE LLAVES CIFRADAS (P-04: solo la clave del proveedor activo) ---
    from src.database import UserConfig
    from src.engine.providers import resolve_keys
    user_config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
    api_key, mistral_key, key_error = resolve_keys(provider, api_key, mistral_key, user_config)
    if key_error and provider != "hybrid":
        raise HTTPException(status_code=400, detail=key_error)

    # Validar que las llaves descifradas no sean vacías o None si el proveedor las requiere
    if provider == "gemini" and not api_key:
        raise HTTPException(
            status_code=400,
            detail="Clave API de Gemini no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes."
        )
    elif provider == "mistral" and not mistral_key:
        raise HTTPException(
            status_code=400,
            detail="Clave API de Mistral no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes."
        )
    elif provider == "groq" and not api_key:
        raise HTTPException(
            status_code=400,
            detail="Clave API de Groq no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes."
        )
    elif provider == "hybrid":
        if not api_key:
            raise HTTPException(status_code=400, detail="Clave API de Gemini no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
        if not mistral_key:
            raise HTTPException(status_code=400, detail="Clave API de Mistral no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")

    try:
        # El origen puede ser un motor SQL o un diccionario de DataFrames
        data_source_obj = session_data["data"]
        if session_data["type"] == "file":
            # Priorizar el archivo seleccionado (data_source_id) si existe
            if data_source_id:
                from src.database import DataSource
                source_obj = db.query(DataSource).filter(DataSource.id == data_source_id, DataSource.user_id == authenticated_user).first()
                if source_obj:
                    safe_name = "".join([c if c.isalnum() else "_" for c in source_obj.name.split('.')[0]])
                    if safe_name in session_data["data"]:
                        data_source_obj = session_data["data"][safe_name]
                    else:
                        # Fallback si no está en memoria por alguna razón
                        data_source_obj = next(iter(session_data["data"].values()))
                else:
                    raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")
            else:
                # Usamos el primer DataFrame si hay varios para el dashboard base
                data_source_obj = next(iter(session_data["data"].values()))
        
        results = generate_auto_dashboard(data_source_obj, api_key, provider, mistral_key)
        from src.utils.common import json_serializable
        return json_serializable({"status": "success", "dashboard": results})
    except HTTPException:
        # P-43: un 404/400 deliberado no es un fallo interno.
        raise
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("Error en auto_dashboard: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error interno al generar el panel automático.")

def _resolve_filter_columns(filters: dict, available_columns: list, available_label: str) -> dict:
    """Resuelve las claves de filtro contra las columnas realmente disponibles.

    P-48: antes una columna inexistente se ignoraba en silencio y el endpoint
    respondía "success" sin filtrar. Ahora una columna que no existe es un
    error de validación (400) con las columnas disponibles a la vista.

    La clave de filtro llega desde el frontend como el nombre de la traza de
    Plotly, no como el nombre exacto de la columna. La resolución va, por
    tanto, de más específica a menos específica:

    1. Coincidencia exacta (sin distinguir mayúsculas/minúsculas ni espacios).
    2. Una columna cuyo nombre está contenido en la clave de la traza
       ("Ventas por Region" → "Region"). Solo si hay una única coincidencia:
       si hay varias, es ambiguo y se rechaza.
    3. Requisición: HTTP 400 con las columnas disponibles a la vista.
    """
    resolved = {}
    normalized = {str(col).strip().lower(): col for col in available_columns}
    for col in filters:
        key = str(col).strip().lower()
        actual = normalized.get(key)
        if actual is None:
            # Fallback: la traza de Plotly suele contener el nombre de la
            # columna. Solo se acepta si la coincidencia es única.
            contained = [
                original for norm, original in normalized.items()
                if norm and norm in key
            ]
            if len(contained) == 1:
                actual = contained[0]
        if actual is None:
            disponibles = ", ".join(str(c) for c in available_columns) or "(ninguna)"
            raise HTTPException(
                status_code=400,
                detail=(
                    f"La columna '{col}' no existe en {available_label}. "
                    f"Columnas disponibles: {disponibles}"
                )
            )
        resolved[actual] = filters[col]
    return resolved


def _filter_file_context(context: dict, filters: dict) -> dict:
    """Filtra un contexto de DataFrames de archivo (modo file).

    Cada DataFrame se filtra con los filtros que apliquen a sus columnas. Una
    columna del filtro que no existe en NINGÚN DataFrame es un error 400; si
    existe en alguno, se aplica solo donde exista.
    """
    frames = {name: df for name, df in context.items() if isinstance(df, pd.DataFrame)}
    if not frames:
        raise HTTPException(
            status_code=400,
            detail="No hay datos tabulares en la sesión para filtrar."
        )

    # Columnas disponibles: la unión de todas las del contexto.
    all_columns = []
    for df in frames.values():
        for col in df.columns:
            if col not in all_columns:
                all_columns.append(col)

    resolved = _resolve_filter_columns(filters, all_columns, "los datos")

    filtered_context = {}
    for name, df in context.items():
        if not isinstance(df, pd.DataFrame):
            filtered_context[name] = df
            continue
        new_df = df.copy()
        for col, val in resolved.items():
            if col in new_df.columns:
                new_df = new_df[new_df[col] == val]
        filtered_context[name] = new_df
    return filtered_context


def _filter_sql_context(context, filters: dict):
    """Filtra una fuente SQL materializando un DataFrame (modo SQL).

    P-48: este modo estaba roto. La rama anterior devolvía el motor SQLAlchemy
    crudo como contexto, y como el sandbox solo serializa DataFrames, el
    código guardado se ejecutaba sin datos (`NameError: name 'df' is not
    defined`).

    Lo correcto es materializar el subconjunto filtrado a un DataFrame y
    ejecutar el código guardado contra él, igual que en modo archivo.

    La consulta se construye con WHERE y los VALORES viajan como parámetros
    bind; los nombres de tabla y columna se validan contra el catálogo vivo
    del engine antes de tocar el string SQL, porque un identificador no se
    puede parameterizar.
    """
    from src.connectors.data_connectors import get_db_schema_structured

    schema = get_db_schema_structured(context)
    if not schema:
        raise HTTPException(
            status_code=400,
            detail="No se pudo leer el esquema de la fuente SQL para filtrar."
        )

    # La columna del filtro debe existir en el catálogo. Se busca en todas las
    # tablas porque el filtro del panel no lleva el nombre de la tabla.
    table_for_column = {}
    all_columns = []
    for entry in schema:
        for col in entry["columns"]:
            if col not in all_columns:
                all_columns.append(col)
            table_for_column.setdefault(col, entry["table"])

    resolved = _resolve_filter_columns(filters, all_columns, "la fuente SQL")

    # Cada filtro se aplica sobre la tabla que contiene su columna.
    conditions = []
    params = {}
    for idx, (col, val) in enumerate(resolved.items()):
        table = table_for_column[col]
        param_name = f"p{idx}"
        conditions.append(f"{col} = :{param_name}")
        params[param_name] = val

    # Una sola tabla: se filtra directamente.
    target_table = table_for_column[next(iter(resolved))]
    if all(table_for_column[col] == target_table for col in resolved):
        where_clause = " AND ".join(conditions)
        sql = f"SELECT * FROM {target_table} WHERE {where_clause}"
    else:
        # Filtros sobre tablas distintas: se combinan con UNION de las
        # tablas implicadas, cada una con sus propias condiciones.
        by_table = {}
        for col, val in resolved.items():
            by_table.setdefault(table_for_column[col], []).append((col, val))
        selects = []
        for tidx, (table, pairs) in enumerate(by_table.items()):
            tconds = []
            tparams = {}
            for cidx, (col, val) in enumerate(pairs):
                pname = f"u{tidx}_p{cidx}"
                tconds.append(f"{col} = :{pname}")
                tparams[pname] = val
            selects.append(f"SELECT * FROM {table} WHERE {' AND '.join(tconds)}")
            params.update(tparams)
        sql = " UNION ALL ".join(selects)

    from src.engine.executor import execute_sql_with_params as _exec_sql
    _, df_result, clean_sql = _exec_sql(context, sql, params)
    if df_result is None:
        logger.error("No se pudo materializar el filtro SQL: %s", sql)
        raise HTTPException(
            status_code=400,
            detail="No se pudo aplicar el filtro sobre la fuente SQL."
        )

    # El sandbox necesita DataFrames. La tabla filtrada se expone con su
    # nombre real para que el código guardado la encuentre, y `var_name` es
    # "dfs" porque el código Python guardado accede a las tablas por nombre.
    return {target_table: df_result}, "dfs"


@router.post("/dashboard/filter")
@limiter.limit("10/minute")
async def filter_dashboard(
    request: Request,
    filters_json: str = Form(...), # JSON string: {"col": "val"}
    db: Session = Depends(get_db)
):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    try:
        filters = json.loads(filters_json)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        # P-36: el bare `except:` también capturaba KeyboardInterrupt/SystemExit.
        # Se acota al error de parseo real del JSON.
        log_ignored_error(
            logger,
            "parseo del JSON de filtros",
            exc,
            level=logging.INFO,
        )
        raise HTTPException(status_code=400, detail="JSON de filtros inválido")

    if not isinstance(filters, dict):
        raise HTTPException(status_code=400, detail="JSON de filtros inválido")

    # P-48: un filtro vacío o sin valor no es un filtro. Antes se respondía
    # "success" sin haber filtrado nada, lo que hacía creer al usuario que el
    # panel estaba filtrado cuando no lo estaba.
    active_filters = {col: val for col, val in filters.items() if val is not None and val != ""}
    if not active_filters:
        raise HTTPException(
            status_code=400,
            detail="No hay filtros activos que aplicar."
        )

    try:
        session_data = get_user_data(authenticated_user)
        if not session_data:
            raise HTTPException(status_code=404, detail="No hay datos cargados en la sesión")

        context = session_data["data"]
        data_type = session_data["type"]

        # Aplicar filtros al contexto. El resultado es SIEMPRE un contexto
        # ejecutable (DataFrames), nunca un motor SQL crudo: el sandbox solo
        # serializa DataFrames y el código guardado se ejecuta contra ellos.
        if data_type == "file":
            filtered_context = _filter_file_context(context, active_filters)
            var_name = "dfs"
        else:
            filtered_context, var_name = _filter_sql_context(context, active_filters)

        items = db.query(DashboardItem).filter(DashboardItem.user_id == authenticated_user).all()
        results = []

        for item in items:
            if not item.message or not item.message.analysis_code:
                continue
            if item.message.analysis_code.startswith(AUDIT_MARKER):
                # La auditoría es una foto determinista del dataset; no se
                # re-ejecuta con filtros porque los hechos quedarían fuera de
                # contexto. Se conserva la figura original.
                results.append({
                    "id": item.id,
                    "fig": json.loads(item.message.figure_json) if item.message.figure_json else None
                })
                continue

            try:
                # Re-ejecutar el código original sobre los datos filtrados
                # execute_analysis espera el raw_response con bloques de código
                _, fig = await execute_analysis(filtered_context, item.message.analysis_code, var_name)

                results.append({
                    "id": item.id,
                    "fig": json.loads(fig.to_json()) if fig else None
                })
            except Exception as e:
                from src.utils.logging_config import safe_error_message
                # P-48: antes el fallo se tragaba con `continue` y el endpoint
                # respondía "success": el cliente no distinguía una figura
                # filtrada de una figura que ni se re-ejecutó.
                logger.error("Error re-filtrando item %d: %s", item.id, safe_error_message(e))
                results.append({
                    "id": item.id,
                    "fig": None,
                    "error": "El análisis no se pudo recalcular con estos filtros."
                })

        return {"status": "success", "updated_items": results}
    except HTTPException as he:
        raise he
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("Error al filtrar panel: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error interno al filtrar el panel.")
