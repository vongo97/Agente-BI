from fpdf import FPDF
import datetime
import io

class BIReport(FPDF):
    def header(self):
        # Linea decorativa superior
        self.set_fill_color(41, 128, 185)
        self.rect(0, 0, 210, 3, 'F')
        
        self.set_y(10)
        self.set_font('helvetica', 'B', 15)
        self.set_text_color(44, 62, 80)
        self.cell(0, 10, 'INFORME EJECUTIVO DE DATOS', 0, 0, 'L')
        
        self.set_font('helvetica', '', 9)
        self.set_text_color(127, 140, 141)
        self.cell(0, 10, f'Generado el: {datetime.datetime.now().strftime("%d/%m/%Y")}', 0, 1, 'R')
        
        self.set_draw_color(230, 230, 230)
        self.line(10, 22, 200, 22)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(189, 195, 199)
        self.cell(0, 10, f'Documento Confidencial - Generado por Agente BI Profesiona - Pagina {self.page_no()}', 0, 0, 'C')

def _clean_text_for_pdf(text):
    """
    Normaliza el texto para evitar errores de codificación en fuentes estándar.
    """
    if not text:
        return ""
    replacements = {
        '€': 'EUR', '$': 'USD', '**': '', '###': '', '#': '', 
        '—': '-', '–': '-', '“': '"', '”': '"', '‘': "'", '’': "'"
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode('latin-1', 'replace').decode('latin-1')

def generate_pdf_report(narrative_text, analysis_summary, fig_image=None):
    """
    Genera un archivo PDF de alta calidad con narrativa y gráfico incrustado.
    """
    narrative_text = _clean_text_for_pdf(narrative_text)
    analysis_summary = _clean_text_for_pdf(analysis_summary)
    
    pdf = BIReport()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    
    # TITULO PRINCIPAL DEL REPORTE
    pdf.set_font('helvetica', 'B', 22)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 20, 'Analisis Estrategico de Operaciones', 0, 1, 'L')
    pdf.ln(5)

    # 1. OBJETIVO DEL ANALISIS
    pdf.set_font('helvetica', 'B', 12)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 10, 'I. ALCANCE Y OBJETIVOS', 0, 1, 'L')
    
    pdf.set_font('helvetica', '', 10)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 6, f"Este documento presenta los resultados del analisis basado en el requerimiento: \"{analysis_summary}\". El objetivo es extraer insights accionables a partir de los datos operativos cargados.")
    pdf.ln(10)
    
    # 2. VISUALIZACIÓN
    if fig_image:
        pdf.set_font('helvetica', 'B', 12)
        pdf.set_text_color(41, 128, 185)
        pdf.cell(0, 10, 'II. EVIDENCIA VISUAL', 0, 1, 'L')
        pdf.ln(2)
        
        img_buffer = io.BytesIO(fig_image)
        try:
            # Calcular ancho para que no se salga
            pdf.image(img_buffer, x=15, w=180)
            pdf.ln(10)
        except:
            pass

    # 3. DIAGNÓSTICO
    pdf.set_font('helvetica', 'B', 12)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 10, 'III. DIAGNOSTICO Y RECOMENDACIONES', 0, 1, 'L')
    pdf.ln(2)
    
    pdf.set_font('helvetica', '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 7, narrative_text)
    
    return bytes(pdf.output())
