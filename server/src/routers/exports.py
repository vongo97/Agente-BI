import os
import logging
import json
from fastapi import APIRouter, HTTPException, Response, Depends, Form, Request
from src.database import get_db, Chat
from src.utils.exporter import export_plotly_to_image, generate_pdf_report
from src.engine.pptx_generator import create_presentation
from src.utils.common import check_authorization, get_authenticated_user
from src.utils.limiter import limiter
from sqlalchemy.orm import Session
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Exports"])

@router.post("/export/chart")
@limiter.limit("10/minute")
@limiter.limit("40/hour")
async def export_chart(request: Request, fig_json: dict):
    try:
        img_bytes = export_plotly_to_image(json.dumps(fig_json))
        if not img_bytes:
            raise HTTPException(status_code=500, detail="Error generando imagen del gráfico")
        
        filename = f"chart_export.png"
        return Response(
            content=img_bytes, 
            media_type="image/png",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("Error al exportar gráfico: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error al generar el gráfico.")

@router.get("/export/pdf/{chat_id}")
@limiter.limit("5/minute")
@limiter.limit("20/hour")
async def export_pdf_report(request: Request, chat_id: int, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == authenticated_user).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")
        
        messages_list = []
        for m in chat.messages:
            messages_list.append({
                "role": m.role,
                "content": m.content,
                "fig": json.loads(m.figure_json) if m.figure_json else None
            })
        
        # Obtener configuración del usuario
        from src.database import UserConfig
        cfg = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
        
        brand_color = cfg.brand_color if cfg and cfg.brand_color else "#2dd4bf"
        report_org_name = cfg.report_org_name if cfg and cfg.report_org_name else "VEKTRA BI"
        report_footer_text = cfg.report_footer_text if cfg and cfg.report_footer_text else "Confidencial - Solo uso interno"
        pdf_orientation = cfg.pdf_orientation if cfg and cfg.pdf_orientation else "portrait"
        
        pdf_bytes = generate_pdf_report(
            user_name=authenticated_user, 
            messages=messages_list,
            brand_color=brand_color,
            report_org_name=report_org_name,
            report_footer_text=report_footer_text,
            pdf_orientation=pdf_orientation
        )
        return Response(
            content=bytes(pdf_bytes), 
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=reporte_bi_{chat_id}.pdf"}
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("Error generando PDF de chat: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error al exportar el reporte PDF.")

@router.post("/export/report")
@limiter.limit("5/minute")
@limiter.limit("20/hour")
async def export_pro_report(request: Request, data: dict, db: Session = Depends(get_db)):
    """
    Genera un Reporte PDF Profesional basado en los datos curados por el usuario.
    """
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    user_name = data.get("user_name", authenticated_user)
    title = data.get("title", "Informe de Análisis BI")
    summary = data.get("summary", "")
    items = data.get("items", []) # Lista de {content, fig}

    from src.utils.exporter import generate_pro_report
    
    # Obtener configuración del usuario
    from src.database import UserConfig
    cfg = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
    
    brand_color = cfg.brand_color if cfg and cfg.brand_color else "#2dd4bf"
    report_org_name = cfg.report_org_name if cfg and cfg.report_org_name else "VEKTRA BI"
    report_footer_text = cfg.report_footer_text if cfg and cfg.report_footer_text else "Confidencial - Solo uso interno"
    pdf_orientation = cfg.pdf_orientation if cfg and cfg.pdf_orientation else "portrait"
    pdf_include_data_table = cfg.pdf_include_data_table if cfg and cfg.pdf_include_data_table is not None else True
    chart_theme = cfg.chart_theme if cfg and cfg.chart_theme else "neon"
    
    try:
        pdf_bytes = generate_pro_report(
            title=title, 
            summary=summary, 
            user_name=user_name, 
            items=items,
            brand_color=brand_color,
            report_org_name=report_org_name,
            report_footer_text=report_footer_text,
            pdf_orientation=pdf_orientation,
            pdf_include_data_table=pdf_include_data_table,
            chart_theme=chart_theme
        )
        return Response(
            content=bytes(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=informe_ejecutivo_{authenticated_user}.pdf"}
        )
    except Exception as e:
        is_render = os.getenv("RENDER", "false").lower() == "true"
        from src.utils.logging_config import safe_error_message
        clean_msg = safe_error_message(e)
        if not is_render:
            logger.exception("Error generando PDF: %s", clean_msg)
        else:
            logger.error("Error generando PDF: %s", clean_msg)
        raise HTTPException(status_code=500, detail="Error generando reporte ejecutivo.")

@router.post("/export-pptx")
@limiter.limit("5/minute")
@limiter.limit("20/hour")
async def export_pptx(request: Request, data: dict, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    title = data.get("title", "Reporte Ejecutivo")
    summary = data.get("summary", "")
    items = data.get("items", [])
    template_type = data.get("template", "general")
    
    # Recuperar la API key del usuario desde la base de datos para la síntesis inteligente
    api_key = None
    try:
        from src.database import UserConfig
        from src.utils.security import decrypt_key
        user_config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
        if user_config and user_config.gemini_key:
            api_key = decrypt_key(user_config.gemini_key)
    except Exception as db_err:
        logger.warning("No se pudo recuperar la API key para PPTX: %s", db_err)
    
    if not items:
        raise HTTPException(status_code=400, detail="Contenido no proporcionado")
        
    template_path = "templates/template_vektra_general.pptx"
    if template_type == "legal":
        template_path = "templates/template_legal.pptx"
    
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp:
        temp_path = tmp.name
    
    try:
        success, result = create_presentation(title, summary, items, temp_path, template_path, api_key=api_key)
        if not success:
            if os.path.exists(temp_path): os.remove(temp_path)
            logger.error("Error generando PPTX: %s", result)
            raise HTTPException(status_code=500, detail="Error interno al generar la presentación PowerPoint.")

        with open(temp_path, "rb") as f:
            file_bytes = f.read()
        
        os.remove(temp_path)
        
        filename = f"presentacion_bi.pptx"
        return Response(
            content=file_bytes,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        if os.path.exists(temp_path): os.remove(temp_path)
        from src.utils.logging_config import safe_error_message
        logger.error("Excepción en exportar PPTX: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error al exportar la presentación PPTX.")

@router.get("/export/simulation/{sim_id}")
@limiter.limit("5/minute")
@limiter.limit("20/hour")
async def export_simulation_pdf(request: Request, sim_id: int, db: Session = Depends(get_db)):
    from src.database import Simulation, SimulationMessage
    from src.utils.exporter import generate_simulation_pdf
    
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    
    try:
        sim = db.query(Simulation).filter(Simulation.id == sim_id, Simulation.user_id == authenticated_user).first()
        if not sim:
            raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")
        
        if not sim.result_report:
            raise HTTPException(status_code=400, detail="La simulación aún no tiene un informe final consolidado.")

        # Obtener el debate para el apéndice
        messages = db.query(SimulationMessage).filter(SimulationMessage.simulation_id == sim_id).order_by(SimulationMessage.created_at).all()
        debate_list = []
        for m in messages:
            debate_list.append({
                "agent_name": m.agent.name if m.agent else "Narrador",
                "agent_role": m.agent.role if m.agent else "Sistema",
                "content": m.content
            })

        pdf_bytes = generate_simulation_pdf(sim.title, sim.hypothesis, sim.result_report, debate_list)
        
        return Response(
            content=bytes(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="ensayo_futuro_{sim_id}.pdf"',
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        from src.utils.logging_config import safe_error_message
        logger.error("Error al exportar PDF de simulación: %s", safe_error_message(e))
        raise HTTPException(status_code=500, detail="Error interno al generar el PDF de simulación.")
