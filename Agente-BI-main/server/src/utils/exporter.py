import io
import json
import plotly.io as pio
import plotly.graph_objects as go
from fpdf import FPDF
import tempfile
import os

def export_plotly_to_image(fig_json_str: str, format: str = "png"):
    """
    Convierte un JSON de Plotly a bytes de imagen (PNG).
    """
    try:
        fig_dict = json.loads(fig_json_str)
        fig = go.Figure(fig_dict)
        # Forzar un layout limpio para exportación
        fig.update_layout(
            paper_bgcolor='white', 
            plot_bgcolor='white', 
            font={'color': 'black', 'size': 14},
            margin=dict(l=40, r=40, t=60, b=40)
        )
        img_bytes = pio.to_image(fig, format=format, engine="kaleido")
        return img_bytes
    except Exception as e:
        print(f"Error exportando imagen: {e}")
        return None

def generate_pdf_report(user_name: str, messages: list):
    """
    Genera un PDF con el historial del chat (Legacy/Simple).
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font("helvetica", 'B', 20)
    pdf.set_text_color(20, 80, 160)
    pdf.cell(0, 15, txt=f"Reporte de Análisis BI (Simple)", ln=True, align='C')
    pdf.ln(5)

    for msg in messages:
        role = "Asistente" if msg['role'] == 'assistant' else "Usuario"
        pdf.set_font("helvetica", 'B', 12)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 10, txt=f"{role}:", ln=True)
        
        pdf.set_font("helvetica", size=10)
        pdf.set_text_color(0, 0, 0)
        content = msg['content'].encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, txt=content)
        pdf.ln(5)
        
        if msg.get('fig'):
            img_bytes = export_plotly_to_image(json.dumps(msg['fig']))
            if img_bytes:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(img_bytes)
                    tmp_path = tmp.name
                try:
                    pdf.image(tmp_path, x=pdf.l_margin, w=pdf.w - 2*pdf.l_margin)
                    pdf.ln(5)
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
    
    return pdf.output()

def generate_pro_report(title: str, summary: str, user_name: str, items: list):
    """
    Genera un Informe Ejecutivo Profesional con Portada y Resumen Estratégico.
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    
    # --- PORTADA ---
    pdf.add_page()
    # Fondo decorativo lateral
    pdf.set_fill_color(20, 80, 160)
    pdf.rect(0, 0, 10, 297, "F")
    
    pdf.ln(60)
    pdf.set_font("helvetica", 'B', 32)
    pdf.set_text_color(33, 33, 33)
    pdf.multi_cell(0, 15, txt=title.upper(), align='L')
    
    pdf.ln(10)
    pdf.set_font("helvetica", '', 16)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, txt="INFORME ESTRATÉGICO DE NEGOCIO", ln=True)
    
    pdf.set_y(250)
    pdf.set_font("helvetica", 'B', 12)
    pdf.set_text_color(20, 80, 160)
    pdf.cell(0, 10, txt=f"CONSULTOR: {user_name.upper()}", ln=True, align='R')
    pdf.set_font("helvetica", '', 10)
    pdf.cell(0, 5, txt=f"GENERADO POR AGENTE BI V2.5", ln=True, align='R')

    # --- RESUMEN EJECUTIVO ---
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 18)
    pdf.set_text_color(20, 80, 160)
    pdf.cell(0, 15, txt="1. RESUMEN EJECUTIVO", ln=True)
    pdf.line(pdf.l_margin, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(10)
    
    pdf.set_font("helvetica", '', 11)
    pdf.set_text_color(0, 0, 0)
    summary_clean = summary.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 7, txt=summary_clean)

    # --- HALLAZGOS Y VISUALIZACIONES ---
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 18)
    pdf.set_text_color(20, 80, 160)
    pdf.cell(0, 15, txt="2. ANÁLISIS DETALLADO", ln=True)
    pdf.line(pdf.l_margin, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(10)

    for i, item in enumerate(items):
        # Título del hallazgo
        pdf.set_font("helvetica", 'B', 14)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(0, 10, txt=f"Hallazgo {i+1}", ln=True)
        
        # Explicación
        pdf.set_font("helvetica", '', 10)
        pdf.set_text_color(30, 30, 30)
        content = item['content'].encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, txt=content)
        pdf.ln(5)
        
        # Gráfico
        if item.get('fig'):
            img_bytes = export_plotly_to_image(json.dumps(item['fig']))
            if img_bytes:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(img_bytes)
                    tmp_path = tmp.name
                try:
                    # Ajustar imagen al ancho de página
                    pdf.image(tmp_path, x=pdf.l_margin + 5, w=pdf.w - (pdf.l_margin * 2) - 10)
                    pdf.ln(10)
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
        
        # Salto de página si no cabe el siguiente
        if pdf.get_y() > 220 and i < len(items) - 1:
            pdf.add_page()

    return pdf.output()
