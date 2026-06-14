import io
import json
import plotly.io as pio
import plotly.graph_objects as go
from fpdf import FPDF
import tempfile
import os
import re
import logging

logger = logging.getLogger(__name__)
from datetime import datetime

def export_plotly_to_image(fig_data: any, format: str = "png"):
    """
    Convierte un objeto/dict de Plotly a bytes de imagen (PNG).
    """
    import unicodedata

    def remove_accents(obj):
        if isinstance(obj, dict):
            return {k: remove_accents(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [remove_accents(i) for i in obj]
        elif isinstance(obj, str):
            return ''.join(c for c in unicodedata.normalize('NFD', obj) if unicodedata.category(c) != 'Mn')
        return obj

    try:
        # Si ya es un dict, no necesitamos json.loads
        fig_dict = fig_data
        if isinstance(fig_data, str):
            fig_dict = json.loads(fig_data)
            
        # Parche UTF-8: Kaleido a veces corrompe tildes en Windows con ciertas fuentes
        fig_dict = remove_accents(fig_dict)
        
        # Asegurar que tenemos data y layout
        if 'data' not in fig_dict:
            # Si no tiene 'data', quizás es el objeto directo
            fig = go.Figure(fig_dict)
        else:
            fig = go.Figure(data=fig_dict.get('data'), layout=fig_dict.get('layout'))
            
        # Forzar un layout limpio y profesional para exportación (Estilo Vektra Light para PDF)
        fig.update_layout(
            paper_bgcolor='white', 
            plot_bgcolor='#f9fafb', 
            font={'color': '#111827', 'family': 'Arial, sans-serif', 'size': 12},
            margin=dict(l=50, r=50, t=80, b=50),
            width=800,
            height=500
        )
        
        # Configurar ejes para que se vean bien en papel
        fig.update_xaxes(gridcolor='#e5e7eb', zerolinecolor='#d1d5db')
        fig.update_yaxes(gridcolor='#e5e7eb', zerolinecolor='#d1d5db')

        # Intentar exportar usando kaleido
        logger.debug("[EXPORT] Exportando gráfico con %d trazas via Kaleido...", len(fig.data))
        img_bytes = pio.to_image(fig, format=format, engine="kaleido", scale=3)
        logger.debug("[EXPORT] Kaleido: %d bytes generados.", len(img_bytes))
        return img_bytes
    except Exception as e:
        logger.warning("[EXPORT] Kaleido falló (%s). Usando fallback Matplotlib.", type(e).__name__)
        return export_to_image_matplotlib_fallback(fig_dict)

def decode_plotly_array(arr_obj):
    """
    Decodifica un arreglo de Plotly, manejando listas normales y objetos binarios (bdata) de JS.
    """
    if arr_obj is None: return []
    
    if isinstance(arr_obj, (list, tuple)):
        return list(arr_obj)
        
    if isinstance(arr_obj, dict) and 'bdata' in arr_obj:
        import base64
        import numpy as np
        dtype_str = arr_obj.get('dtype', 'float64')
        bdata = arr_obj.get('bdata')
        
        dtype_map = {
            'float64': np.float64, 'float32': np.float32,
            'int32': np.int32, 'int16': np.int16, 'int8': np.int8,
            'uint32': np.uint32, 'uint16': np.uint16, 'uint8': np.uint8,
        }
        try:
            raw_bytes = base64.b64decode(bdata)
            arr = np.frombuffer(raw_bytes, dtype=dtype_map.get(dtype_str, np.float64))
            return arr.tolist()
        except Exception as e:
            logger.error("[EXPORT] Error decodificando bdata: %s", type(e).__name__)
            return []
            
    return []

def export_to_image_matplotlib_fallback(fig_dict: dict):
    """
    Motor de respaldo avanzado usando Matplotlib.
    Decodifica directamente del JSON original para evadir la corrupción de go.Figure.
    """
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
        import numpy as np
        
        # Estilo premium y mayor espacio horizontal para que no se corten
        plt.style.use('fast')
        fig_plt, ax = plt.subplots(figsize=(14, 7))
        
        data_list = fig_dict.get('data', [])
        if not data_list:
            return None
            
        # Contar trazas de barra para calcular desplazamientos (grouped bars)
        bar_traces = [t for t in data_list if t.get('type', 'scatter') in ['bar', 'histogram']]
        total_bars = len(bar_traces)
        bar_width = 0.8 / total_bars if total_bars > 0 else 0.8
        current_bar = 0
            
        for trace in data_list:
            chart_type = trace.get('type', 'scatter')
            
            x = decode_plotly_array(trace.get('x'))
            y = decode_plotly_array(trace.get('y'))
            name = trace.get('name', '')
            
            if not x or not y: continue
            
            # Sincronizar longitudes de X y Y para evitar el error 'shape mismatch' de Matplotlib
            min_len = min(len(x), len(y))
            if min_len == 0: continue
            x = x[:min_len]
            y = y[:min_len]
            
            # Extraer color de la traza si está disponible
            colors = '#2563eb'
            marker = trace.get('marker', {})
            if marker and 'color' in marker:
                c_val = marker.get('color')
                if isinstance(c_val, (list, tuple, np.ndarray)):
                    c_list = list(c_val)
                    if len(c_list) >= min_len:
                        colors = c_list[:min_len]
                    elif len(c_list) > 0:
                        colors = (c_list * ((min_len // len(c_list)) + 1))[:min_len]
                elif c_val is not None:
                    colors = c_val
            
            if chart_type in ['bar', 'histogram']:
                # Agrupar barras lado a lado en lugar de solaparlas
                x_numeric = np.arange(len(x))
                offset = (current_bar - total_bars/2 + 0.5) * bar_width
                
                bars = ax.bar(x_numeric + offset, y, width=bar_width, label=name, color=colors, alpha=0.85, edgecolor='white', linewidth=0.5)
                
                # Configurar las etiquetas del eje X al final
                if current_bar == total_bars - 1 or total_bars == 1:
                    ax.set_xticks(x_numeric)
                    ax.set_xticklabels(x)
                    
                current_bar += 1
            elif chart_type == 'pie':
                ax.pie(y, labels=x, autopct='%1.1f%%', colors=sns.color_palette("Blues_r"))
            else:
                if isinstance(colors, list): colors = colors[0] if colors else '#2563eb'
                ax.plot(x, y, marker='o', label=name, color=colors, linewidth=2.5, markersize=8)

        # Configuración estética leyendo el layout
        layout = fig_dict.get('layout', {})
        raw_title = layout.get('title', {}).get('text', 'Análisis Estratégico') if isinstance(layout.get('title'), dict) else 'Análisis Estratégico'
        clean_title = re.sub(r'<[^>]*>', '', raw_title) if isinstance(raw_title, str) else 'Análisis Estratégico'
        
        ax.set_title(clean_title, fontsize=16, pad=25, fontweight='bold', color='#111827')
        ax.set_facecolor('#fcfcfc')
        ax.grid(True, axis='y', linestyle='--', alpha=0.4, color='#cbd5e1')
        
        # Etiquetas
        xaxis_title = layout.get('xaxis', {}).get('title', {}).get('text', '') if isinstance(layout.get('xaxis'), dict) and isinstance(layout.get('xaxis').get('title'), dict) else ''
        yaxis_title = layout.get('yaxis', {}).get('title', {}).get('text', '') if isinstance(layout.get('yaxis'), dict) and isinstance(layout.get('yaxis').get('title'), dict) else ''
        
        if xaxis_title and isinstance(xaxis_title, str): ax.set_xlabel(re.sub(r'<[^>]*>', '', xaxis_title), fontweight='bold')
        if yaxis_title and isinstance(yaxis_title, str): ax.set_ylabel(re.sub(r'<[^>]*>', '', yaxis_title), fontweight='bold')

        # Rotación inteligente de etiquetas
        plt.xticks(rotation=45, ha='right', fontsize=9)
        if len(data_list) > 1:
            # Colocar la leyenda fuera del área de trazado para evitar superposiciones
            ax.legend(loc='upper left', bbox_to_anchor=(1, 1), frameon=True, facecolor='white', shadow=True)
            
        plt.tight_layout()
        
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        plt.close()
        
        return img_buffer.getvalue()
    except Exception as ex:
        logger.error("[EXPORT] Fallback crítico Matplotlib: %s", type(ex).__name__)
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
        content = clean_text(msg['content'])
        pdf.multi_cell(0, 6, txt=content)
        pdf.ln(5)
        
        if msg.get('fig'):
            img_bytes = export_plotly_to_image(msg['fig'])
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

class PremiumBIReport(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.alias_nb_pages()
        
    def header(self):
        if self.page_no() == 1:
            return
        # Encabezado con línea fina de acento y texto formal
        self.set_draw_color(37, 99, 235) # Azul Vektra
        self.set_line_width(0.5)
        # Margen izquierdo es 15, derecho es 15, por lo que la línea va de 15 a 195 (210 - 15)
        self.line(15, 15, 195, 15)
        
        self.set_y(8)
        self.set_font('helvetica', 'B', 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, 'INFORME DE ANÁLISIS ESTRATÉGICO - VEKTRA BI', 0, 1, 'L')
        
        # CORRECCIÓN: Evitar que el texto empiece a escribirse en Y=13 y choque con la línea en Y=15
        self.set_y(22)
        
    def footer(self):
        if self.page_no() == 1:
            return
        # Pie de página: numeración formal ("Página X de Y") y fecha.
        self.set_y(-15)
        self.set_font('helvetica', '', 8)
        self.set_text_color(150, 150, 150)
        date_str = datetime.now().strftime("%d/%m/%Y")
        
        # Fecha alineada a la izquierda y número de página alineado a la derecha
        self.cell(100, 10, f'Fecha: {date_str}', 0, 0, 'L')
        self.cell(0, 10, f'Página {self.page_no()} de {{nb}}', 0, 0, 'R')

def get_multicell_height(pdf, text, width):
    lines = text.split('\n')
    total_lines = 0
    for line in lines:
        if not line:
            total_lines += 1
            continue
        w = pdf.get_string_width(line)
        import math
        sub_lines = max(1, math.ceil(w / width))
        total_lines += sub_lines
    return total_lines * 6

def draw_card(pdf, text, bg_color=(240, 244, 248), border_color=(14, 116, 144)):
    # Calcular ancho disponible y ancho del texto considerando paddings
    avail_w = pdf.w - pdf.l_margin - pdf.r_margin
    text_w = avail_w - 8 # 4mm de padding interno a cada lado
    
    # Calcular la altura necesaria con la fuente de 10
    pdf.set_font("helvetica", '', 10)
    card_h = get_multicell_height(pdf, text, text_w) + 6 # 3mm de padding arriba y abajo
    
    # Verificar salto de página preventivo
    if pdf.get_y() + card_h > pdf.page_break_trigger:
        pdf.add_page()
        
    start_x = pdf.get_x()
    start_y = pdf.get_y()
    
    # Dibujar fondo de la tarjeta
    pdf.set_fill_color(*bg_color)
    pdf.rect(start_x, start_y, avail_w, card_h, 'F')
    
    # Dibujar borde izquierdo grueso (de color azul/verde/teal)
    pdf.set_fill_color(*border_color)
    pdf.rect(start_x, start_y, 1.5, card_h, 'F')
    
    # Dibujar el texto
    pdf.set_text_color(55, 65, 81) # Charcoal
    pdf.set_xy(start_x + 5, start_y + 3)
    pdf.multi_cell(text_w, 6, txt=text, border=0)
    
    # Actualizar cursor de posición con un margen de 4mm después de la tarjeta
    pdf.set_y(start_y + card_h + 4)

def generate_pro_report(title: str, summary: str, user_name: str, items: list):
    """
    Genera un Informe Ejecutivo Profesional con Portada y Resumen Estratégico.
    """
    # Control de Errores: Reemplazo silencioso de errores de autenticación técnica en el resumen ejecutivo
    error_indicators = ["error de autenticación con gemini", "error de autenticacion", "api key", "autenticación", "gemini api error"]
    if any(ind in summary.lower() for ind in error_indicators):
        summary = "Por favor, configure sus claves API en Ajustes para generar este resumen."

    pdf = PremiumBIReport()
    pdf.set_margins(15, 20, 15) # Margen izquierdo 15, superior 20, derecho 15
    pdf.set_auto_page_break(auto=True, margin=20)
    
    # --- PORTADA PREMIUM (DARK MODE STYLE) ---
    pdf.add_page()
    # Fondo oscuro para la portada
    pdf.set_fill_color(15, 15, 15)
    pdf.rect(0, 0, 210, 297, "F")
    
    # Acento de color lateral (Azul Vektra)
    pdf.set_fill_color(37, 99, 235)
    pdf.rect(0, 0, 5, 297, "F")
    
    pdf.set_y(80)
    pdf.set_font("helvetica", 'B', 36)
    pdf.set_text_color(255, 255, 255)
    pdf.multi_cell(0, 18, txt=clean_text(title).upper(), align='L')
    
    pdf.ln(5)
    pdf.set_font("helvetica", 'B', 14)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(0, 10, txt="DIAGNÓSTICO ESTRATÉGICO DE DATOS", ln=True)
    
    pdf.set_y(240)
    pdf.set_font("helvetica", 'B', 10)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, txt="PREPARADO POR:", ln=True, align='R')
    pdf.set_font("helvetica", 'B', 14)
    pdf.set_text_color(255, 255, 255)
    
    # Formatear el nombre por si es un correo o tiene números/caracteres
    formatted_name = user_name
    if "@" in formatted_name:
        formatted_name = formatted_name.split("@")[0]
    formatted_name = re.sub(r'\d+$', '', formatted_name)
    formatted_name = formatted_name.replace(".", " ").replace("_", " ").replace("-", " ")
    formatted_name = formatted_name.title().strip()
        
    pdf.cell(0, 10, txt=clean_text(formatted_name).upper(), ln=True, align='R')
    
    pdf.ln(5)
    pdf.set_font("helvetica", 'B', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, txt=f"VEKTRA BI ENGINE | {datetime.now().strftime('%Y')}", ln=True, align='R')

    # --- RESUMEN EJECUTIVO ---
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 18)
    pdf.set_text_color(20, 80, 160)
    pdf.cell(0, 15, txt="1. RESUMEN EJECUTIVO", ln=True)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(10)
    
    summary_clean = clean_text(summary)
    paragraphs = [p.strip() for p in summary_clean.split('\n\n') if p.strip()]
    for p in paragraphs:
        # Usar un color de acento azul (#2563eb) para la tarjeta del resumen
        draw_card(pdf, p, bg_color=(240, 244, 248), border_color=(37, 99, 235))

    # --- HALLAZGOS Y VISUALIZACIONES ---
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 18)
    pdf.set_text_color(20, 80, 160)
    pdf.cell(0, 15, txt="2. ANÁLISIS DETALLADO", ln=True)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(10)

    for i, item in enumerate(items):
        # Título del hallazgo (usar título si existe, o extraer primera línea)
        pdf.set_font("helvetica", 'B', 14)
        pdf.set_text_color(20, 80, 160)
        
        item_title = item.get('title')
        if not item_title:
            # Extraer primera frase o línea como título
            first_line = item['content'].split('\n')[0].strip('# ').strip()
            item_title = first_line if len(first_line) > 5 else f"Análisis de Datos {i+1}"
            
        pdf.multi_cell(0, 10, txt=clean_text(item_title).upper())
        pdf.ln(2)
        
        # Explicación y Tablas
        content = clean_text(item['content'])
        lines = content.split('\n')
        
        # Parsear líneas en elementos de tipo "text" (párrafos) o "table" (lista de celdas)
        elements = []
        current_text = []
        current_table = []
        
        for line in lines:
            line_str = line.strip()
            if line_str.startswith('|') and line_str.endswith('|'):
                # Fila de tabla
                if current_text:
                    elements.append(("text", "\n".join(current_text)))
                    current_text = []
                
                cells = [c.strip() for c in line_str.split('|')[1:-1]]
                if all(c.replace('-', '').replace(':', '').strip() == '' for c in cells if c):
                    continue
                current_table.append(cells)
            else:
                # Línea de texto normal
                if current_table:
                    elements.append(("table", current_table))
                    current_table = []
                current_text.append(line)
                
        if current_text:
            elements.append(("text", "\n".join(current_text)))
        if current_table:
            elements.append(("table", current_table))
            
        # Renderizar elementos
        for elem_type, elem_content in elements:
            if elem_type == "text":
                paragraphs = [p.strip() for p in elem_content.split('\n\n') if p.strip()]
                for p in paragraphs:
                    # Renderizar texto libre con fuente elegante y espaciado profesional en vez de tarjetas repetitivas
                    pdf.set_font("helvetica", '', 10)
                    pdf.set_text_color(30, 41, 59) # Slate Oscuro (Texto Principal)
                    
                    # Salto preventivo para evitar que una línea huérfana salte de página
                    if pdf.get_y() + 15 > pdf.page_break_trigger:
                        pdf.add_page()
                        
                    pdf.multi_cell(0, 6, txt=p)
                    pdf.ln(4) # Espaciado entre párrafos
            elif elem_type == "table":
                rows = elem_content
                if not rows:
                    continue
                
                # Control preventivo de salto de página para tablas
                h_table = len(rows) * 6 + 10
                if pdf.get_y() + h_table > pdf.page_break_trigger:
                    pdf.add_page()
                    
                # Dibujar tabla
                for row_idx, cells in enumerate(rows):
                    col_w = (pdf.w - pdf.l_margin - pdf.r_margin) / max(1, len(cells))
                    
                    if row_idx == 0:
                        # Estilo cabecera de la tabla
                        pdf.set_font("helvetica", 'B', 8)
                        pdf.set_text_color(255, 255, 255)
                        pdf.set_fill_color(37, 99, 235) # Azul Vektra
                        pdf.set_draw_color(37, 99, 235)
                    else:
                        # Estilo filas de datos
                        pdf.set_font("helvetica", '', 8)
                        pdf.set_text_color(55, 65, 81)
                        if row_idx % 2 == 0:
                            pdf.set_fill_color(243, 244, 246) # Zebra striping
                        else:
                            pdf.set_fill_color(255, 255, 255)
                        pdf.set_draw_color(229, 231, 235)
                        
                    for cell in cells:
                        pdf.cell(col_w, 6, txt=cell[:45], border=1, fill=True)
                    pdf.ln(6)
                pdf.ln(4)
        
        # Gráfico
        if item.get('fig'):
            img_bytes = export_plotly_to_image(item['fig'])
            if img_bytes:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(img_bytes)
                    tmp_path = tmp.name
                try:
                    # Centrar y ajustar imagen
                    avail_width = pdf.w - pdf.l_margin - pdf.r_margin
                    
                    # Control preventivo de salto de página para gráficos
                    if pdf.get_y() + 100 > pdf.page_break_trigger:
                        pdf.add_page()
                        
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
    """Limpia el texto eliminando artefactos de markdown y caracteres no soportados por latin-1"""
    if not text: return ""
    
    import re
    
    # 1. Primero eliminar todos los emojis UTF-8 (reemplazándolos por "")
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    text = re.sub(r'[\u2600-\u27bf\u2300-\u23ff\ufe0f]', '', text)
    
    # Reemplazar otros caracteres especiales de puntuación
    replacements = {
        "•": "-", "—": "-", "–": "-",
        "“": '"', "”": '"', "‘": "'", "’": "'"
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
        
    text = text.replace("**", "")
    text = text.replace("* ", " - ")
    
    # Eliminar #, ##, ### del inicio de las líneas
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    
    # Eliminar por completo las líneas enteras de subtítulos específicos (y sus variantes)
    text = re.sub(r'^.*Análisis de Impacto\s*\(¿Qué está pasando\?\).*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^.*Recomendaciones\s*\(¿Qué debemos hacer\?\).*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    
    # Eliminar etiquetas internas del sistema y subtítulos técnicos redundantes sin dejar prefijos
    text = re.sub(r'^\s*(DATA|ANALISIS|INFO|REGLA DE ORO|RECOMENDACIONES|ATENCION|TIP|OBJETIVO|ALERTA|DIAGNÓSTICO ESTRATÉGICO|DIAGNOSTICO ESTRATEGICO):\s*([^\n]*?:\s*)?', '', text, flags=re.MULTILINE|re.IGNORECASE)
    
    # Limpiar espacios a nivel de línea pero conservar los dobles saltos de línea para mantener los párrafos separados
    lines = [line.strip() for line in text.split("\n")]
    cleaned_lines = []
    for line in lines:
        if line == "":
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
        else:
            cleaned_lines.append(line)
    text = "\n".join(cleaned_lines)
    
    # 3. Codificar de forma segura para FPDF (Latin-1)
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
