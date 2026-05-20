import os
import json
from fastapi import APIRouter, HTTPException, Response, Depends, Form
from src.database import get_db, Chat
from src.utils.exporter import export_plotly_to_image, generate_pdf_report
from src.engine.pptx_generator import create_presentation
from src.utils.common import check_authorization
from sqlalchemy.orm import Session

router = APIRouter(tags=["Exports"])

@router.post("/export/chart")
async def export_chart(fig_json: dict):
    img_bytes = export_plotly_to_image(json.dumps(fig_json))
    if not img_bytes:
        raise HTTPException(status_code=500, detail="Error generando imagen del gráfico")
    
    filename = f"chart_export.png"
    return Response(
        content=img_bytes, 
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/export/pdf/{chat_id}")
async def export_pdf_report(chat_id: int, user_id: str, db: Session = Depends(get_db)):
    check_authorization(user_id)
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    
    messages_list = []
    for m in chat.messages:
        messages_list.append({
            "role": m.role,
            "content": m.content,
            "fig": json.loads(m.figure_json) if m.figure_json else None
        })
    
    pdf_bytes = generate_pdf_report(user_id, messages_list)
    return Response(
        content=bytes(pdf_bytes), 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=reporte_bi_{chat_id}.pdf"}
    )

@router.post("/export/report")
async def export_pro_report(data: dict):
    """
    Genera un Reporte PDF Profesional basado en los datos curados por el usuario.
    """
    user_id = data.get("user_id", "Invitado")
    user_name = data.get("user_name", user_id)
    title = data.get("title", "Informe de Análisis BI")
    summary = data.get("summary", "")
    items = data.get("items", []) # Lista de {content, fig}

    from src.utils.exporter import generate_pro_report
    
    try:
        pdf_bytes = generate_pro_report(title, summary, user_name, items)
        return Response(
            content=bytes(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=informe_ejecutivo_{user_id}.pdf"}
        )
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error generando reporte pro: {str(e)}")

@router.post("/export-pptx")
async def export_pptx(data: dict):
    title = data.get("title", "Reporte Ejecutivo")
    summary = data.get("summary", "")
    items = data.get("items", [])
    
    if not items:
        raise HTTPException(status_code=400, detail="Contenido no proporcionado")
    
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp:
        temp_path = tmp.name
    
    success, result = create_presentation(title, summary, items, temp_path)
    
    if not success:
        if os.path.exists(temp_path): os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"Error generando PPTX: {result}")

    with open(temp_path, "rb") as f:
        file_bytes = f.read()
    
    os.remove(temp_path)
    
    filename = f"presentacion_bi.pptx"
    return Response(
        content=file_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/export/simulation/{sim_id}")
async def export_simulation_pdf(sim_id: int, user_id: str, db: Session = Depends(get_db)):
    from src.database import Simulation, SimulationMessage
    from src.utils.exporter import generate_simulation_pdf
    
    # Limpiar posibles espacios o caracteres raros en el user_id
    clean_user_id = user_id.strip()
    
    sim = db.query(Simulation).filter(Simulation.id == sim_id, Simulation.user_id == clean_user_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail=f"Simulación {sim_id} no encontrada para el usuario {clean_user_id}")
    
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
