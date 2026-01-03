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
    Genera un PDF con el historial del chat y las imágenes de los gráficos.
    """
    # fpdf2 usa 'helvetica' como estándar compatible con UTF-8 básico
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Título principal
    pdf.set_font("helvetica", 'B', 20)
    pdf.set_text_color(20, 80, 160)
    pdf.cell(0, 15, txt=f"Reporte de Análisis BI", ln=True, align='C')
    
    pdf.set_font("helvetica", 'I', 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, txt=f"Usuario: {user_name}", ln=True, align='C')
    pdf.ln(10)

    for msg in messages:
        role = "Consultor BI" if msg['role'] == 'assistant' else "Usuario"
        
        # Encabezado del mensaje
        pdf.set_font("helvetica", 'B', 12)
        if msg['role'] == 'assistant':
            pdf.set_text_color(0, 102, 204)
        else:
            pdf.set_text_color(51, 51, 51)
            
        pdf.cell(0, 10, txt=f"{role}:", ln=True)
        
        # Contenido del mensaje (Texto)
        pdf.set_font("helvetica", size=10)
        pdf.set_text_color(0, 0, 0)
        # Limpiar caracteres que no son latin-1 si no se usa una fuente unicode externa
        content = msg['content'].encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, txt=content)
        pdf.ln(5)
        
        # Gráficos
        if msg.get('fig'):
            img_bytes = export_plotly_to_image(json.dumps(msg['fig']))
            if img_bytes:
                # Usar archivo temporal único para evitar conflictos entre usuarios
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(img_bytes)
                    tmp_path = tmp.name
                
                try:
                    # Centrar imagen
                    page_width = pdf.w - 2 * pdf.l_margin
                    pdf.image(tmp_path, x=pdf.l_margin, w=page_width)
                    pdf.ln(5)
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
    
    return pdf.output() # En fpdf2, output() sin argumentos devuelve bytes
