import io
import json
import plotly.io as pio
import plotly.graph_objects as go
from fpdf import FPDF

def export_plotly_to_image(fig_json_str: str, format: str = "png"):
    """
    Convierte un JSON de Plotly a bytes de imagen (PNG).
    """
    try:
        fig_dict = json.loads(fig_json_str)
        fig = go.Figure(fig_dict)
        # Forzar un layout limpio para exportación
        fig.update_layout(paper_bgcolor='white', plot_bgcolor='white', font={'color': 'black'})
        img_bytes = pio.to_image(fig, format=format, engine="kaleido")
        return img_bytes
    except Exception as e:
        print(f"Error exportando imagen: {e}")
        return None

def generate_pdf_report(user_name: str, messages: list):
    """
    Genera un PDF con el historial del chat y las imágenes de los gráficos.
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Título
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=f"Reporte de Análisis BI - {user_name}", ln=True, align='C')
    pdf.ln(10)

    for msg in messages:
        role = "Asistente" if msg['role'] == 'assistant' else "Usuario"
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt=f"{role}:", ln=True)
        
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 5, txt=msg['content'])
        pdf.ln(5)
        
        if msg.get('fig'):
            # Si hay un gráfico, lo convertimos a imagen temporalmente y lo añadimos
            img_bytes = export_plotly_to_image(json.dumps(msg['fig']))
            if img_bytes:
                img_stream = io.BytesIO(img_bytes)
                # FPDF acepta rutas o streams en algunas versiones, 
                # si no, guardamos temporalmente. 
                # Para simplificar, usaremos una imagen temporal
                with open("temp_chart.png", "wb") as f:
                    f.write(img_bytes)
                pdf.image("temp_chart.png", x=10, w=180)
                pdf.ln(5)
    
    # Limpiar
    import os
    if os.path.exists("temp_chart.png"):
        os.remove("temp_chart.png")
        
    return pdf.output(dest='S') # Retorna bytes
