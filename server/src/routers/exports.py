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
async def export_pdf_report(request: Request, chat_id: int, user_id: Optional[str] = None, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == authenticated_user).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat no encontrado")
        
        messages_list = []
        for m in chat.messages:
            messages_list.append({
                "role": m.role,
                "content": m.content,
                "fig": json.loads(m.figure_json) if m.figure_json else None
            })
        
        pdf_bytes = generate_pdf_report(authenticated_user, messages_list)
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
async def export_pro_report(request: Request, data: dict):
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
    
    try:
        pdf_bytes = generate_pro_report(title, summary, user_name, items)
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
async def export_pptx(request: Request, data: dict):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    title = data.get("title", "Reporte Ejecutivo")
    summary = data.get("summary", "")
    items = data.get("items", [])
    template_type = data.get("template", "general")
    
    if not items:
        raise HTTPException(status_code=400, detail="Contenido no proporcionado")
        
    template_path = "templates/template_vektra_general.pptx"
    if template_type == "legal":
        template_path = "templates/template_legal.pptx"
    
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp:
        temp_path = tmp.name
    
    try:
        success, result = create_presentation(title, summary, items, temp_path, template_path)
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
async def export_simulation_pdf(request: Request, sim_id: int, user_id: Optional[str] = None, db: Session = Depends(get_db)):
    from src.database import Simulation, SimulationMessage
    from src.utils.exporter import generate_simulation_pdf
    
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    
    try:
        sim = db.query(Simulation).filter(Simulation.id == sim_id, Simulation.user_id == authenticated_user).first()
        if not sim:
            raise HTTPException(status_code=404, detail=f"Simulación {sim_id} no encontrada para el usuario {authenticated_user}")
        
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
