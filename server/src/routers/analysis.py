import asyncio
import json
import os
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
from src.database import get_db, Chat, Message, UserConfig, DataSource
from src.engine.bi_analyst import analyze_data, execute_analysis, suggest_questions, validate_data_quality
from src.engine.audit_agent import (
    audit_agent_enabled,
    build_audit_payload,
    generate_audit_narrative,
    is_audit_query,
)
from src.engine.insight_auditor import AUDIT_MARKER, AuditError, build_audit
from src.engine.executor import execute_sql_safe, validate_sql_safety
from src.engine.prompts import SQL_ENGINEER_PROMPT
from src.engine.providers import generate_ai_content
from src.utils.common import check_authorization, get_user_data, get_authenticated_user, ensure_user_session
from src.utils.security import decrypt_key

from src.utils.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Analysis"])

# El narrador de auditoría es opcional: si el proveedor tarda, se devuelve la
# narrativa determinista (que ya contiene las cifras verificadas) en vez de
# mantener la petición abierta varios minutos.
try:
    _AUDIT_NARRATOR_TIMEOUT_S = float(os.getenv("AUDIT_NARRATOR_TIMEOUT_S", "25"))
except (TypeError, ValueError):
    _AUDIT_NARRATOR_TIMEOUT_S = 25.0


def _audit_figure_json(audit) -> Optional[dict]:
    figure = audit.get("figure")
    return json.loads(figure.to_json()) if figure is not None and hasattr(figure, "to_json") else None


def _save_audit_message(db: Session, chat_id: int, content: str, fig_json, payload: dict) -> Message:
    from src.utils.common import SafeJSONEncoder

    assistant_msg = Message(
        chat_id=chat_id,
        role="assistant",
        content=content,
        figure_json=json.dumps(fig_json, cls=SafeJSONEncoder) if fig_json else None,
        analysis_code=AUDIT_MARKER + json.dumps(payload, cls=SafeJSONEncoder),
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg


def _narrator_credentials(provider: str, api_key: Optional[str], mistral_key: Optional[str]):
    """Elige una sola credencial para el narrador; nunca mezcla proveedores."""
    if provider == "hybrid":
        if mistral_key:
            return "mistral", mistral_key
        return "gemini", api_key
    if provider == "mistral":
        return "mistral", mistral_key
    return provider, api_key


@router.post("/analyze")
@limiter.limit("5/minute")
@limiter.limit("30/hour")
async def analyze(
    request: Request,
    query: str = Form(...),
    api_key: str = Form(...),
    chat_id: Optional[int] = Form(None),
    data_source_id: Optional[int] = Form(None),
    provider: str = Form("gemini"),
    mistral_key: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    audit_requested = audit_agent_enabled() and is_audit_query(query)

    # Cargar la configuración del usuario una única vez para API keys y parámetros adicionales
    user_config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
    user_temp = user_config.temperature if user_config and user_config.temperature is not None else 0.2

    if chat_id:
        chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == authenticated_user).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")

    if data_source_id:
        source = db.query(DataSource).filter(DataSource.id == data_source_id, DataSource.user_id == authenticated_user).first()
        if not source:
            raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")
    
    # --- AUTO-RECUPERACIÓN DE LLAVES CIFRADAS ---
    from src.engine.providers import resolve_keys, get_model, set_model_override
    api_key, mistral_key, key_error = resolve_keys(provider, api_key, mistral_key, user_config)
    # Modelo elegido por el usuario en Ajustes. Viaja por ContextVar para que las diez
    # funciones del motor lo vean sin añadir un parámetro a cada una.
    set_model_override(get_model(provider, user_config))
    if not audit_requested:
        if key_error and provider != "hybrid":
            raise HTTPException(status_code=400, detail=key_error)

        if provider == "hybrid":
            if not api_key:
                raise HTTPException(
                    status_code=400,
                    detail="Clave API de Gemini no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes."
                )
            if not mistral_key:
                raise HTTPException(
                    status_code=400,
                    detail="Clave API de Mistral no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes."
                )
    
    # Filtro de saludos
    greetings = ["hola", "hi", "hey", "buenos dias", "buenas tardes", "buenas noches"]
    if query.strip().lower() in greetings:
        msg = "¡Hola! Soy Vektra. ¿Qué te gustaría analizar de tus datos hoy?"
        new_msg = Message(chat_id=chat_id, role="assistant", content=msg)
        db.add(new_msg); db.commit()
        return {"analysis": msg, "chat_id": chat_id, "message_id": new_msg.id}

    # Si no hay data_source_id pero hay chat_id, intentar recuperarlo del chat
    if chat_id and not data_source_id:
        db_chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == authenticated_user).first()
        if db_chat and db_chat.data_source_id:
            data_source_id = db_chat.data_source_id
 
    # DIAGNÓSTICO — pasan por el filtro de secretos del logger
    logger.debug("Analyze Request: user=%s, chat=%s, source=%s, provider=%s",
                 authenticated_user, chat_id, data_source_id, provider)
    
    # Descifrar/unpicklear la sesión puede tardar; no debe bloquear el event loop.
    session_data = await asyncio.to_thread(get_user_data, authenticated_user, chat_id)
    logger.debug("Session Data found: %s", session_data is not None)
    
    # Verificar si la fuente solicitada está en el pool actual
    is_source_in_pool = session_data is not None and data_source_id and (
        session_data.get("source_id") == data_source_id or 
        data_source_id in session_data.get("sources", [])
    )
    
    if session_data is not None and data_source_id and not is_source_in_pool:
        logger.debug("Source Mismatch: request=%s not in pool %s",
                     data_source_id, session_data.get('sources', []))
        # Solo descartar la sesión si el pool está completamente vacío.
        has_data = bool(session_data.get("data"))
        if not has_data:
            session_data = None
        # Si has_data == True, conservamos session_data para que la segunda pregunta
        # pueda acceder a los archivos que ya estaban en el pool.

    if session_data is None:
        # Reconstruir el pool desde DB+nube (post-reinicio del contenedor);
        # incluye la autocarga de la fuente solicitada si está registrada.
        from src.utils.common import ensure_user_session
        # Reconstruir el pool descarga/descifra/parsea archivos; se hace fuera
        # del event loop para que /live siga respondiendo.
        session_data = await asyncio.to_thread(
            ensure_user_session, authenticated_user, db, chat_id
        )
        
        if not session_data:
            logger.warning("No session data found or loaded for user (source=%s).", data_source_id)
            raise HTTPException(status_code=400, detail="No hay datos cargados para analizar. Por favor selecciona una fuente de datos.")
    
    try:
        # Determinar el tipo de dato y la variable
        data_type = session_data["type"]

        # --- MODO SQL: Materialización Segura previa al análisis (P-03) ---
        if data_type == "sql":
            engine = session_data["data"]
            schema = session_data.get("schema") or ""

            if not api_key and not mistral_key:
                raise HTTPException(
                    status_code=400,
                    detail="Se requiere una clave de API configurada para analizar bases de datos SQL."
                )

            sql_key = mistral_key if provider == "mistral" else api_key
            sql_provider = provider if provider != "hybrid" else "gemini"

            sql_prompt = SQL_ENGINEER_PROMPT.format(context_str=schema, query=query)
            raw_sql_response = await asyncio.to_thread(
                generate_ai_content,
                sql_prompt,
                sql_key,
                sql_provider,
                temperature=0.0
            )

            execution_msg, df_result, clean_sql = execute_sql_safe(engine, raw_sql_response)
            if df_result is None or df_result.empty:
                error_response = execution_msg or "La consulta SQL no produjo resultados o fue rechazada por seguridad."
                new_msg = Message(chat_id=chat_id, role="assistant", content=error_response)
                db.add(new_msg); db.commit()
                return {"analysis": error_response, "chat_id": chat_id, "message_id": new_msg.id}

            data_to_analyze = df_result
            data_var = "df"
        else:
            data_to_analyze = session_data["data"]
            data_var = "dfs" if isinstance(data_to_analyze, dict) else "df"

        # Determinar el nombre de la fuente primaria para el aislamiento de contexto
        primary_source_name = None
        if data_source_id:
            source_obj = db.query(DataSource).filter(DataSource.id == data_source_id, DataSource.user_id == authenticated_user).first()
            if source_obj:
                primary_source_name = "".join([c if c.isalnum() else "_" for c in source_obj.name.split('.')[0]])
        
        # --- FILTRO DE CALIDAD ---
        is_valid, reason = validate_data_quality(data_to_analyze)
        if not is_valid:
            content = f"### ⚠️ Lo sentimos, archivo no compatible\n{reason}\n\n**Sugerencia:** Por favor, asegúrate de subir un archivo con datos estructurados (filas y columnas) que contenga al menos una columna de números (métricas)."
            new_msg = Message(chat_id=chat_id, role="assistant", content=content)
            db.add(new_msg); db.commit()
            return {"analysis": content, "chat_id": chat_id, "message_id": new_msg.id}

        if audit_requested and data_type == "file":
            # --- AGENTE DE AUDITORÍA (Fase 2, opt-in) ---
            # Los hechos se calculan con pandas; el LLM solo selecciona IDs y
            # redacta un marco sin cifras. El servidor inserta los valores
            # exactos junto al título y la definición de cada hecho.
            db_chat = None
            if chat_id:
                db_chat = db.query(Chat).filter(
                    Chat.id == chat_id, Chat.user_id == authenticated_user
                ).first()
                if not db_chat:
                    raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")

            source_name = None
            audit_primary_name = None
            if data_source_id:
                source_obj = db.query(DataSource).filter(
                    DataSource.id == data_source_id, DataSource.user_id == authenticated_user
                ).first()
                if source_obj:
                    source_name = source_obj.name
                    audit_primary_name = "".join(
                        [c if c.isalnum() else "_" for c in source_obj.name.split('.')[0]]
                    )
            elif db_chat and db_chat.data_source:
                source_name = db_chat.data_source.name
                audit_primary_name = "".join(
                    [c if c.isalnum() else "_" for c in source_name.split('.')[0]]
                )

            audit = None
            try:
                # build_audit recorre el DataFrame con pandas (CPU). Se ejecuta
                # fuera del event loop para no bloquear los health checks.
                audit = await asyncio.to_thread(
                    build_audit,
                    data_to_analyze,
                    primary_source_name=audit_primary_name,
                    source_name=source_name,
                )
            except AuditError as exc:
                # Un dataset sin columnas auditables no debe romper /analyze:
                # se continúa con el camino normal, que aplicará sus claves.
                logger.info("Auditoría Fase 2 no aplicable; se usa el flujo normal: %s", exc)
                audit_requested = False

            if audit_requested and audit is not None:
                narrator_provider, narrator_key = _narrator_credentials(provider, api_key, mistral_key)
                try:
                    narrative, narrative_mode, fallback_reason = await asyncio.wait_for(
                        asyncio.to_thread(
                            generate_audit_narrative,
                            query,
                            audit,
                            api_key=narrator_key,
                            provider=narrator_provider,
                            temperature=user_temp,
                        ),
                        timeout=max(1.0, _AUDIT_NARRATOR_TIMEOUT_S),
                    )
                except asyncio.TimeoutError:
                    narrative = str(audit.get("analysis") or "Auditoría completada.")
                    narrative_mode = "deterministic"
                    fallback_reason = "timeout_narrador"
                if fallback_reason:
                    logger.info("Auditoría Fase 2 usó narrativa determinista: %s", fallback_reason)

                payload = build_audit_payload(audit, narrative_mode)
                fig_json = _audit_figure_json(audit)

                if db_chat is None:
                    db_chat = Chat(
                        user_id=authenticated_user,
                        title=query[:50] + "...",
                        data_source_id=data_source_id,
                    )
                    db.add(db_chat)
                    db.commit()
                    db.refresh(db_chat)
                    from src.utils.common import promote_active_session
                    promote_active_session(authenticated_user, db_chat.id)

                user_msg = Message(chat_id=db_chat.id, role="user", content=query)
                db.add(user_msg)
                assistant_msg = _save_audit_message(
                    db, db_chat.id, narrative, fig_json, payload
                )

                from src.utils.common import json_serializable
                return json_serializable({
                    "chat_id": db_chat.id,
                    "message_id": assistant_msg.id,
                    "analysis": narrative,
                    "figure": fig_json,
                    "audit": payload,
                    "narrative_mode": narrative_mode,
                })

        # Si la auditoría no aplica (SQL, dataset no auditable o flag apagado),
        # se aplican las validaciones de clave que se difirieron al inicio.
        if key_error and provider != "hybrid":
            raise HTTPException(status_code=400, detail=key_error)
        if provider == "hybrid" and (not api_key or not mistral_key):
            raise HTTPException(
                status_code=400,
                detail="El proveedor híbrido requiere las claves de Gemini y Mistral."
            )

        # 1. Obtener análisis, gráfico y código de la IA
        output_text, fig, raw_response = await analyze_data(
            data_to_analyze, 
            query, 
            api_key, 
            mode="file", 
            provider=provider, 
            mistral_key=mistral_key,
            primary_source_name=primary_source_name,
            temperature=user_temp
        )
        
        fig_json = json.loads(fig.to_json()) if fig and hasattr(fig, 'to_json') else fig
        
        # ── P-54: verificación numérica también en el flujo general de /analyze ──
        # Siempre que sea posible, calcular hechos verificables con pandas y
        # adjuntarlos a la respuesta. El frontend renderiza InsightCards cuando
        # hay audit, por lo que el usuario ve cifras verificadas junto a la
        # narrativa del LLM. Si el dataset no es auditable, se continúa sin
        # payload de auditoría (no romper el flujo normal).
        audit_payload = None
        audit_narrative_mode = None
        try:
            audit = await asyncio.to_thread(
                build_audit,
                data_to_analyze,
                primary_source_name=primary_source_name,
                source_name=source_name,
            )
            audit_payload = build_audit_payload(audit, "deterministic")
            audit_narrative_mode = "deterministic"
            # Enriquecer la narrativa del LLM con los hechos verificados si el
            # LLM no aportó cifras verificables.
            if audit_payload and audit_payload.get("insights"):
                verified_facts = "\n".join(
                    f"• {f.get('title', '')}: {f.get('display_value', '')}"
                    for f in audit_payload["insights"][:5]
                )
                output_text = (
                    f"{output_text}\n\n---\n**Hechos verificados (pandas, sin LLM):**\n{verified_facts}"
                )
        except AuditError:
            # Dataset no auditable: continuar con el flujo normal sin auditoría.
            pass
        
        # Persistencia
        if chat_id:
            db_chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == authenticated_user).first()
        else:
            db_chat = Chat(
                user_id=authenticated_user, 
                title=query[:50] + "...",
                data_source_id=data_source_id
            )
            db.add(db_chat)
            db.commit()
            db.refresh(db_chat)
            # Promocionar los datos de la sesión activa al nuevo chat ID
            from src.utils.common import promote_active_session
            promote_active_session(authenticated_user, db_chat.id)
        
        user_msg = Message(chat_id=db_chat.id, role="user", content=query)
        db.add(user_msg)
        
        from src.utils.common import SafeJSONEncoder, json_serializable
        assistant_msg = Message(
            chat_id=db_chat.id, 
            role="assistant", 
            content=output_text,
            figure_json=json.dumps(fig_json, cls=SafeJSONEncoder) if fig_json else None,
            analysis_code=raw_response
        )
        db.add(assistant_msg)
        db.commit()
            
        from src.utils.common import json_serializable
        return json_serializable({
            "chat_id": db_chat.id,
            "message_id": assistant_msg.id,
            "analysis": output_text,
            "figure": fig_json,
            "code": raw_response,
            "audit": audit_payload,
            "narrative_mode": audit_narrative_mode,
        })
    except HTTPException:
        db.rollback()
        raise
    except AuditError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        is_render = os.getenv("RENDER", "false").lower() == "true"
        from src.utils.logging_config import safe_error_message
        clean_msg = safe_error_message(e)
        if not is_render:
            logger.exception("ERROR 500 /analyze [%s]: %s", type(e).__name__, clean_msg)
        else:
            logger.error("ERROR 500 /analyze [%s]: %s", type(e).__name__, clean_msg)
        raise HTTPException(status_code=500, detail="Error interno del servidor al procesar el análisis de datos.")

@router.post("/analyze/audit")
@limiter.limit("10/minute")
@limiter.limit("60/hour")
def analyze_audit(
    request: Request,
    chat_id: Optional[int] = Form(None),
    data_source_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """Auditoría determinista y verificable (Fase 1 de P-54).

    No usa LLM ni API key: calcula hechos con pandas, los expone con
    definición/evidencia y renderiza una narrativa a partir de ellos.
    """
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)

    db_chat = None
    if chat_id:
        db_chat = db.query(Chat).filter(
            Chat.id == chat_id, Chat.user_id == authenticated_user
        ).first()
        if not db_chat:
            raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")
        if not data_source_id and db_chat.data_source_id:
            data_source_id = db_chat.data_source_id

    source_obj = None
    if data_source_id:
        source_obj = db.query(DataSource).filter(
            DataSource.id == data_source_id, DataSource.user_id == authenticated_user
        ).first()
        if not source_obj:
            raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")

    try:
        session_data = get_user_data(authenticated_user, chat_id)
        if session_data is None:
            session_data = ensure_user_session(authenticated_user, db, chat_id)
        if not session_data:
            raise HTTPException(
                status_code=400,
                detail="No hay datos cargados para auditar. Por favor selecciona una fuente de datos."
            )
        pool_ids = set()
        if session_data.get("source_id") is not None:
            pool_ids.add(session_data.get("source_id"))
        for source_id in session_data.get("sources", []) or []:
            pool_ids.add(source_id)
        if data_source_id and pool_ids and data_source_id not in pool_ids:
            raise HTTPException(
                status_code=400,
                detail="La fuente solicitada no está cargada en esta conversación. Vuelve a seleccionarla antes de auditar."
            )
        if session_data.get("type") != "file":
            raise HTTPException(
                status_code=400,
                detail="La auditoría verificada Fase 1 solo está disponible para archivos CSV/Excel. "
                       "El modo SQL sigue pendiente (P-03)."
            )

        is_valid, reason = validate_data_quality(session_data.get("data"))
        if not is_valid:
            raise HTTPException(status_code=400, detail=reason)

        primary_source_name = None
        source_name = None
        if source_obj:
            source_name = source_obj.name
            primary_source_name = "".join(
                [c if c.isalnum() else "_" for c in source_obj.name.split('.')[0]]
            )
        elif db_chat and db_chat.data_source:
            source_name = db_chat.data_source.name
            primary_source_name = "".join(
                [c if c.isalnum() else "_" for c in source_name.split('.')[0]]
            )

        audit = build_audit(
            session_data.get("data"),
            primary_source_name=primary_source_name,
            source_name=source_name,
        )

        fig_json = _audit_figure_json(audit)
        payload = build_audit_payload(audit, "deterministic")

        if db_chat is None:
            title_source = (audit.get("source_name") or "dataset").strip()
            db_chat = Chat(
                user_id=authenticated_user,
                title=f"Auditoría verificada: {title_source[:55]}",
                data_source_id=data_source_id,
            )
            db.add(db_chat)
            db.commit()
            db.refresh(db_chat)
            from src.utils.common import promote_active_session
            promote_active_session(authenticated_user, db_chat.id)

        from src.utils.common import json_serializable
        assistant_msg = _save_audit_message(
            db,
            db_chat.id,
            audit.get("analysis") or "Auditoría completada.",
            fig_json,
            payload,
        )

        return json_serializable({
            "chat_id": db_chat.id,
            "message_id": assistant_msg.id,
            "analysis": audit.get("analysis"),
            "figure": fig_json,
            "audit": payload,
        })
    except HTTPException:
        db.rollback()
        raise
    except AuditError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        from src.utils.logging_config import safe_error_message
        logger.error("ERROR /analyze/audit [%s]: %s", type(e).__name__, safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error interno al generar la auditoría verificada.")


@router.post("/suggest-questions")
@limiter.limit("10/minute")
@limiter.limit("60/hour")
def get_suggestions(
    request: Request,
    api_key: str = Form(...),
    chat_id: Optional[int] = Form(None), # AÑADIDO
    data_source_id: Optional[int] = Form(None),
    provider: str = Form("gemini"),
    mistral_key: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)

    # Configuración del usuario (aqui se definen las claves y el modo luego)
    user_config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()

    if chat_id:
        chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == authenticated_user).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")

    if data_source_id:
        source = db.query(DataSource).filter(DataSource.id == data_source_id, DataSource.user_id == authenticated_user).first()
        if not source:
            raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")
    
    # --- AUTO-RECUPERACIÓN DE LLAVES CIFRADAS ---
    from src.engine.providers import resolve_keys, get_model, set_model_override
    api_key, mistral_key, key_error = resolve_keys(provider, api_key, mistral_key, user_config)
    # Modelo elegido por el usuario en Ajustes. Viaja por ContextVar para que las diez
    # funciones del motor lo vean sin añadir un parámetro a cada una.
    set_model_override(get_model(provider, user_config))
    if key_error and provider != "hybrid":
        raise HTTPException(status_code=400, detail=key_error)
 
    session_data = get_user_data(authenticated_user, chat_id)
    
    # VALIDACIÓN DE FUENTE: Si el ID solicitado no está en el pool, forzar recarga
    is_source_in_pool = session_data and data_source_id and (
        session_data.get("source_id") == data_source_id or 
        data_source_id in session_data.get("sources", [])
    )
 
    if session_data and data_source_id and not is_source_in_pool:
        session_data = None
 
    if not session_data:
        # Reconstruir el pool desde DB+nube (post-reinicio del contenedor)
        from src.utils.common import ensure_user_session
        session_data = ensure_user_session(authenticated_user, db, chat_id)

    if not session_data:
        raise HTTPException(status_code=404, detail="No hay datos cargados para generar sugerencias.")
    
    suggestions = []
    try:
        context = session_data["data"]
        
        # Determinar el nombre de la fuente primaria para el aislamiento de contexto
        primary_source_name = None
        if data_source_id:
            source_obj = db.query(DataSource).filter(DataSource.id == data_source_id, DataSource.user_id == authenticated_user).first()
            if source_obj:
                primary_source_name = "".join([c if c.isalnum() else "_" for c in source_obj.name.split('.')[0]])

        if session_data["type"] == "sql":
            from src.connectors.data_connectors import get_db_schema
            context = get_db_schema(session_data["data"])

        suggestions = suggest_questions(
            context, 
            api_key, 
            mode=session_data["type"], 
            provider=provider, 
            mistral_key=mistral_key,
            primary_source_name=primary_source_name
        )
    except Exception as e:
        logger.warning("Suggest Questions error (non-critical): %s", type(e).__name__)
        suggestions = ["¿Qué insights hay en los datos?"]
        
    return {"suggestions": suggestions}

@router.post("/detect-anomalies")
@limiter.limit("10/minute")
async def detect_anomalies(request: Request, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    
    user_config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
    anomaly_threshold = user_config.anomaly_sensitivity if user_config and user_config.anomaly_sensitivity is not None else 2.5
    
    session_data = ensure_user_session(authenticated_user, db)
    if not session_data or "data" not in session_data or not session_data["data"]:
        raise HTTPException(
            status_code=400, 
            detail="No hay fuentes de datos activas en tu sesión para auditar."
        )
        
    import numpy as np
    import pandas as pd
    
    report_lines = []
    report_lines.append("# 🔍 Informe de Auditoría y Detección de Anomalías")
    report_lines.append(f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    
    anomalies_found = False
    
    for table_name, df in session_data["data"].items():
        if not isinstance(df, pd.DataFrame):
            continue
            
        report_lines.append(f"## 📋 Tabla: `{table_name}`")
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if not num_cols:
            report_lines.append("No se encontraron columnas numéricas para auditar en esta tabla.\n")
            continue
            
        # Intentar buscar columnas descriptivas (nombre, fecha, etc.) para contextualizar la fila
        str_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        context_cols = [c for c in str_cols if any(keyword in c.lower() for keyword in ["name", "nombre", "id", "key", "product", "producto", "date", "fecha", "category", "categoria"])]
        # Tomar máximo las primeras 3 columnas de contexto
        context_cols = context_cols[:3]
        if not context_cols and str_cols:
            context_cols = str_cols[:2]
            
        table_anomalies = []
        
        for col in num_cols:
            # Ignorar columnas tipo ID numérico o códigos
            if any(k in col.lower() for k in ["id", "codigo", "code", "zip", "phone", "telefono"]):
                continue
                
            col_data = df[col].dropna()
            if len(col_data) < 5:
                continue
                
            mean = col_data.mean()
            std = col_data.std()
            
            if std == 0 or pd.isna(std):
                continue
                
            z_scores = (col_data - mean) / std
            outliers = col_data[z_scores.abs() > anomaly_threshold]
            
            if not outliers.empty:
                anomalies_found = True
                for idx, val in outliers.items():
                    # Obtener contexto
                    row = df.loc[idx]
                    context_info = []
                    for c_col in context_cols:
                        context_info.append(f"{c_col}: **{row[c_col]}**")
                    context_str = ", ".join(context_info) if context_info else f"Fila #{idx}"
                    
                    z_val = z_scores.loc[idx]
                    deviation_dir = "superior a la media" if z_val > 0 else "inferior a la media"
                    
                    table_anomalies.append({
                        "columna": col,
                        "contexto": context_str,
                        "valor": val,
                        "z_score": z_val,
                        "desviacion": deviation_dir,
                        "media": mean,
                        "std": std
                    })
                    
        if table_anomalies:
            # Ordenar por el valor absoluto del Z-Score (las más extremas primero)
            table_anomalies.sort(key=lambda x: abs(x["z_score"]), reverse=True)
            
            # Limitar a las 10 anomalías más severas por tabla para evitar spam
            severity_limit = 10
            top_anomalies = table_anomalies[:severity_limit]
            
            report_lines.append(f"Se han detectado **{len(table_anomalies)}** anomalías estadísticas utilizando el algoritmo Z-Score (Umbral > {anomaly_threshold:.1f}σ).\n")
            report_lines.append("| Columna | Contexto / Fila | Valor Registrado | Desviación (Z-Score) | Media de la Columna |")
            report_lines.append("| :--- | :--- | :--- | :--- | :--- |")
            for an in top_anomalies:
                # Formatear el valor
                val_str = f"{an['valor']:,.2f}" if isinstance(an['valor'], float) else f"{an['valor']:,}"
                mean_str = f"{an['media']:,.2f}"
                report_lines.append(
                    f"| `{an['columna']}` | {an['contexto']} | **{val_str}** | {an['z_score']:.2f}σ ({an['desviacion']}) | {mean_str} |"
                )
            report_lines.append("")
            
            if len(table_anomalies) > severity_limit:
                report_lines.append(f"*Nota: Se muestran solo las {severity_limit} anomalías más extremas de un total de {len(table_anomalies)}.*\n")
        else:
            report_lines.append(f"✓ No se detectaron anomalías severas en las métricas de esta tabla (todas las filas se encuentran dentro del rango de ±{anomaly_threshold:.1f} desviaciones estándar).\n")
            
    if not anomalies_found:
        report_lines.append("\n### 🟢 Diagnóstico de Salud de Datos: Excelente")
        report_lines.append("El detective de datos no encontró valores atípicos significativos. Los datos presentan una distribución estadística estable y homogénea.")
    else:
        report_lines.append("\n### ⚠️ Recomendación Estratégica")
        report_lines.append("Revisa los valores atípicos detectados. En procesos de BI, las anomalías superiores a menudo indican picos inusuales de rendimiento (ej. campañas muy exitosas) o errores de facturación, mientras que las inferiores pueden representar fugas de transacciones o fallos de registro.")
        
    return {"analysis": "\n".join(report_lines)}

@router.post("/generate-report-summary")
@limiter.limit("5/minute")
def get_report_summary(
    request: Request,
    query: str = Form(...),
    api_key: str = Form(...),
    provider: str = Form("gemini"),
    mistral_key: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    
    # --- AUTO-RECUPERACIÓN DE LLAVES CIFRADAS ---
    from src.engine.providers import resolve_keys
    user_config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
    api_key, mistral_key, key_error = resolve_keys(provider, api_key, mistral_key, user_config)
    if key_error and provider != "hybrid":
        raise HTTPException(status_code=400, detail=key_error)
            
    session_data = ensure_user_session(authenticated_user, db)
    
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
