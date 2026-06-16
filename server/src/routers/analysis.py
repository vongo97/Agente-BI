import json
import os
import logging
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
from src.database import get_db, Chat, Message, UserConfig, DataSource
from src.engine.bi_analyst import analyze_data, execute_analysis, suggest_questions, validate_data_quality
from src.utils.common import check_authorization, get_user_data, get_authenticated_user
from src.utils.security import decrypt_key

from src.utils.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Analysis"])

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
    if len(api_key) < 10 or "..." in api_key or provider == "groq" or (provider == "mistral" and (not mistral_key or len(mistral_key) < 10 or "..." in mistral_key)):
        if user_config:
            if provider == "groq" and user_config.groq_key:
                api_key = decrypt_key(user_config.groq_key)
            elif (len(api_key) < 10 or "..." in api_key) and user_config.gemini_key:
                api_key = decrypt_key(user_config.gemini_key)
            if provider == "mistral" and (not mistral_key or len(mistral_key) < 10 or "..." in mistral_key) and user_config.mistral_key:
                mistral_key = decrypt_key(user_config.mistral_key)
    else:
        # Si vienen del frontend pero están cifradas (empiezan por gAAAA), las desciframos
        api_key = decrypt_key(api_key)
        if mistral_key: mistral_key = decrypt_key(mistral_key)
    
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
    
    session_data = get_user_data(authenticated_user, chat_id)
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
        # Intentar auto-cargar desde DataSource si tenemos el ID
        if data_source_id:
            logger.debug("Attempting auto-load for source %s", data_source_id)
            from src.utils.common import load_source_to_session
            source = db.query(DataSource).filter(DataSource.id == data_source_id, DataSource.user_id == authenticated_user).first()
            if source:
                success = load_source_to_session(authenticated_user, source, chat_id)
                logger.debug("Auto-load success: %s", success)
                if success:
                    session_data = get_user_data(authenticated_user, chat_id)
        
        if not session_data:
            logger.warning("No session data found or loaded for user (source=%s).", data_source_id)
            raise HTTPException(status_code=400, detail="No hay datos cargados para analizar. Por favor selecciona una fuente de datos.")
    
    try:
        # Determinar el tipo de dato y la variable
        data_type = session_data["type"]
        data_var = "dfs" if data_type == "file" else "engine"

        # Determinar el nombre de la fuente primaria para el aislamiento de contexto
        primary_source_name = None
        if data_source_id:
            source_obj = db.query(DataSource).filter(DataSource.id == data_source_id, DataSource.user_id == authenticated_user).first()
            if source_obj:
                primary_source_name = "".join([c if c.isalnum() else "_" for c in source_obj.name.split('.')[0]])
        
        # --- FILTRO DE CALIDAD ---
        is_valid, reason = validate_data_quality(session_data["data"])
        if not is_valid:
            content = f"### ⚠️ Lo sentimos, archivo no compatible\n{reason}\n\n**Sugerencia:** Por favor, asegúrate de subir un archivo con datos estructurados (filas y columnas) que contenga al menos una columna de números (métricas)."
            new_msg = Message(chat_id=chat_id, role="assistant", content=content)
            db.add(new_msg); db.commit()
            return {"analysis": content, "chat_id": chat_id, "message_id": new_msg.id}
        
        # 1. Obtener análisis, gráfico y código de la IA
        output_text, fig, raw_response = await analyze_data(
            session_data["data"], 
            query, 
            api_key, 
            mode=data_type, 
            provider=provider, 
            mistral_key=mistral_key,
            primary_source_name=primary_source_name,
            temperature=user_temp
        )
        
        fig_json = json.loads(fig.to_json()) if fig and hasattr(fig, 'to_json') else fig
            
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
            "code": raw_response
        })
    except Exception as e:
        is_render = os.getenv("RENDER", "false").lower() == "true"
        from src.utils.logging_config import safe_error_message
        clean_msg = safe_error_message(e)
        if not is_render:
            logger.exception("ERROR 500 /analyze [%s]: %s", type(e).__name__, clean_msg)
        else:
            logger.error("ERROR 500 /analyze [%s]: %s", type(e).__name__, clean_msg)
        raise HTTPException(status_code=500, detail="Error interno del servidor al procesar el análisis de datos.")

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

    if chat_id:
        chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == authenticated_user).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")

    if data_source_id:
        source = db.query(DataSource).filter(DataSource.id == data_source_id, DataSource.user_id == authenticated_user).first()
        if not source:
            raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")
    
    # --- AUTO-RECUPERACIÓN DE LLAVES CIFRADAS ---
    if len(api_key) < 10 or "..." in api_key or provider == "groq" or (provider == "mistral" and (not mistral_key or len(mistral_key) < 10 or "..." in mistral_key)):
        user_config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
        if user_config:
            if provider == "groq" and user_config.groq_key:
                api_key = decrypt_key(user_config.groq_key)
            elif (len(api_key) < 10 or "..." in api_key) and user_config.gemini_key:
                api_key = decrypt_key(user_config.gemini_key)
            if provider == "mistral" and (not mistral_key or len(mistral_key) < 10 or "..." in mistral_key) and user_config.mistral_key:
                mistral_key = decrypt_key(user_config.mistral_key)
    else:
        api_key = decrypt_key(api_key)
        if mistral_key:
            mistral_key = decrypt_key(mistral_key)
 
    # Validar que las llaves descifradas no sean vacías o None si el proveedor las requiere
    if provider == "gemini" and not api_key:
        raise HTTPException(status_code=400, detail="Clave API de Gemini no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
    elif provider == "mistral" and not mistral_key:
        raise HTTPException(status_code=400, detail="Clave API de Mistral no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
    elif provider == "groq" and not api_key:
        raise HTTPException(status_code=400, detail="Clave API de Groq no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
 
    session_data = get_user_data(authenticated_user, chat_id)
    
    # VALIDACIÓN DE FUENTE: Si el ID solicitado no está en el pool, forzar recarga
    is_source_in_pool = session_data and data_source_id and (
        session_data.get("source_id") == data_source_id or 
        data_source_id in session_data.get("sources", [])
    )
 
    if session_data and data_source_id and not is_source_in_pool:
        session_data = None
 
    if not session_data:
        # Intentar auto-cargar desde DataSource si tenemos el ID
        if data_source_id:
            from src.utils.common import load_source_to_session
            source = db.query(DataSource).filter(DataSource.id == data_source_id, DataSource.user_id == authenticated_user).first()
            if source and load_source_to_session(authenticated_user, source, chat_id):
                session_data = get_user_data(authenticated_user, chat_id)

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
    
    session_data = get_user_data(authenticated_user)
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
    if len(api_key) < 10 or "..." in api_key or provider == "groq" or (provider == "mistral" and (not mistral_key or len(mistral_key) < 10 or "..." in mistral_key)):
        user_config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
        if user_config:
            if provider == "groq" and user_config.groq_key:
                api_key = decrypt_key(user_config.groq_key)
            elif (len(api_key) < 10 or "..." in api_key) and user_config.gemini_key:
                api_key = decrypt_key(user_config.gemini_key)
            if provider == "mistral" and (not mistral_key or len(mistral_key) < 10 or "..." in mistral_key) and user_config.mistral_key:
                mistral_key = decrypt_key(user_config.mistral_key)
    else:
        api_key = decrypt_key(api_key)
        if mistral_key:
            mistral_key = decrypt_key(mistral_key)
            
    # Validar que las llaves descifradas no sean vacías o None si el proveedor las requiere
    if provider == "gemini" and not api_key:
        raise HTTPException(status_code=400, detail="Clave API de Gemini no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
    elif provider == "mistral" and not mistral_key:
        raise HTTPException(status_code=400, detail="Clave API de Mistral no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
    elif provider == "groq" and not api_key:
        raise HTTPException(status_code=400, detail="Clave API de Groq no válida o corrupta. Por favor, re-ingresa tu clave API en Ajustes.")
            
    session_data = get_user_data(authenticated_user)
    
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
