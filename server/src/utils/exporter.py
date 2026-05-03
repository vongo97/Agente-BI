import io
import json
import plotly.io as pio
import plotly.graph_objects as go
from fpdf import FPDF
import tempfile
import os
from datetime import datetime

def export_plotly_to_image(fig_json_str: str, format: str = "png"):
    """
    Convierte un JSON de Plotly a bytes de imagen (PNG) con fallback seguro.
    """
    try:
        fig_dict = json.loads(fig_json_str)
        fig = go.Figure(fig_dict)
        fig.update_layout(
            paper_bgcolor='white', 
            plot_bgcolor='white', 
            font={'color': 'black', 'size': 14},
            margin=dict(l=40, r=40, t=60, b=40)
        )
        # Intentamos usar Kaleido
        img_bytes = pio.to_image(fig, format=format)
        return img_bytes
    except Exception as e:
        print(f"[DEBUG] El motor de imágenes falló, pero el reporte continuará: {e}")
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
    pdf.multi_cell(0, 7, txt=clean_text(summary))

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
        pdf.set_text_color(20, 80, 160)
        
        item_title = item.get('title')
        if not item_title:
            first_line = item['content'].split('\n')[0].strip('# ').strip()
            item_title = first_line if len(first_line) > 5 else f"Análisis de Datos {i+1}"
            
        pdf.multi_cell(0, 10, txt=clean_text(item_title).upper())
        pdf.ln(2)
        
        # Explicación
        pdf.set_font("helvetica", '', 10)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 6, txt=clean_text(item['content']))
        pdf.ln(5)
        
        # Gráfico
        if item.get('fig'):
            img_bytes = export_plotly_to_image(json.dumps(item['fig']))
            if img_bytes:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(img_bytes)
                    tmp_path = tmp.name
                try:
                    # Centrar y ajustar imagen
                    avail_width = pdf.w - (pdf.l_margin * 2)
                    pdf.image(tmp_path, x=pdf.l_margin, w=avail_width)
                    pdf.ln(10)
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
        
        # Salto de página si no cabe el siguiente
        if pdf.get_y() > 220 and i < len(items) - 1:
            pdf.add_page()

    return pdf.output()

def clean_text(text: str):
    """Limpia el texto para que sea compatible con Latin-1 (fuentes estándar de FPDF)"""
    if not text: return ""
    # Reemplazar caracteres comunes que dan problemas
    text = text.replace("•", "-").replace("—", "-").replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    return text.encode('latin-1', 'replace').decode('latin-1')

def generate_simulation_pdf(title: str, hypothesis: str, report: str, debate_messages: list):
    """
    Genera un PDF profesional para los Ensayos del Futuro (Simulaciones).
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    
    # --- PORTADA ---
    pdf.add_page()
    # Barra lateral púrpura (color del simulador)
    pdf.set_fill_color(147, 51, 234) 
    pdf.rect(0, 0, 10, 297, "F")
    
    pdf.ln(60)
    pdf.set_font("helvetica", 'B', 28)
    pdf.set_text_color(33, 33, 33)
    pdf.multi_cell(0, 15, txt=clean_text(f"ENSAYO DEL FUTURO: {title.upper()}"), align='L')
    
    pdf.ln(10)
    pdf.set_font("helvetica", 'B', 14)
    pdf.set_text_color(147, 51, 234)
    pdf.cell(0, 10, txt=clean_text("REPORTE DE TRAYECTORIA Y PROSPECTIVA"), ln=True)
    
    pdf.ln(20)
    pdf.set_font("helvetica", 'I', 11)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 6, txt=clean_text(f"HIPOTESIS ANALIZADA:\n{hypothesis}"))

    pdf.set_y(250)
    pdf.set_font("helvetica", 'B', 10)
    pdf.set_text_color(147, 51, 234)
    pdf.cell(0, 10, txt=clean_text("VEKTRA BI ENGINE | MIROFISH LITE"), ln=True, align='R')
    pdf.set_font("helvetica", '', 8)
    pdf.cell(0, 5, txt=clean_text(f"FECHA DE INFERENCIA: {datetime.now().strftime('%Y-%m-%d %H:%M')}"), ln=True, align='R')

    # --- INFORME FINAL (CONCLUSIÓN) ---
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 18)
    pdf.set_text_color(147, 51, 234)
    pdf.cell(0, 15, txt=clean_text("VEREDICTO DEL ENJAMBRE"), ln=True)
    pdf.line(pdf.l_margin, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(10)
    
    pdf.set_font("helvetica", '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 7, txt=clean_text(report))

    # --- REGISTRO DEL DEBATE (APÉNDICE) ---
    if debate_messages:
        pdf.add_page()
        pdf.set_font("helvetica", 'B', 16)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 15, txt=clean_text("APENDICE: REGISTRO DE TRANSCRIPCION"), ln=True)
        pdf.ln(5)
        
        for msg in debate_messages:
            pdf.set_font("helvetica", 'B', 10)
            pdf.set_text_color(147, 51, 234)
            pdf.cell(0, 8, txt=clean_text(f"[{msg['agent_role']}] {msg['agent_name']}:"), ln=True)
            
            pdf.set_font("helvetica", '', 9)
            pdf.set_text_color(40, 40, 40)
            pdf.multi_cell(0, 5, txt=clean_text(msg['content']))
            pdf.ln(4)

    # Para fpdf2, output() sin argumentos devuelve bytes directamente
    return pdf.output()
