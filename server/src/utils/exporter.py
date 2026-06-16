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

def export_plotly_to_image(fig_data: any, format: str = "png", theme: str = "neon"):
    """
    Convierte un objeto/dict de Plotly a bytes de imagen (PNG) aplicando temas visuales.
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
            
        # Configurar el layout según el tema elegido
        bg_paper = 'white'
        bg_plot = '#f9fafb'
        font_color = '#111827'
        grid_color = '#e5e7eb'
        zeroline_color = '#d1d5db'

        if theme == "neon":
            bg_paper = '#0f172a' # Slate 900
            bg_plot = '#1e293b'  # Slate 800
            font_color = '#f8fafc'
            grid_color = '#334155'
            zeroline_color = '#475569'
        elif theme == "dark_glass":
            bg_paper = '#18181b' # Zinc 900
            bg_plot = 'rgba(39, 39, 42, 0.6)' # Zinc 800 translúcido
            font_color = '#f4f4f5'
            grid_color = '#3f3f46'
            zeroline_color = '#52525b'
        elif theme == "vibrant":
            bg_paper = '#fafafa' # Neutral 50
            bg_plot = '#f5f5f5'  # Neutral 100
            font_color = '#171717'
            grid_color = '#d4d4d8'
            zeroline_color = '#a1a1aa'

        fig.update_layout(
            paper_bgcolor=bg_paper, 
            plot_bgcolor=bg_plot, 
            font={'color': font_color, 'family': 'Arial, sans-serif', 'size': 12},
            margin=dict(l=50, r=50, t=80, b=50),
            width=800,
            height=500
        )
        
        # Configurar ejes
        fig.update_xaxes(gridcolor=grid_color, zerolinecolor=zeroline_color)
        fig.update_yaxes(gridcolor=grid_color, zerolinecolor=zeroline_color)

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
            # Códigos cortos de Javascript typed arrays
            'f8': np.float64, 'f4': np.float32,
            'i4': np.int32, 'i2': np.int16, 'i1': np.int8,
            'u4': np.uint32, 'u2': np.uint16, 'u1': np.uint8,
            'i8': np.int64, 'u8': np.uint64
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
            
        # 1. Recopilar todas las categorías únicas del eje X en orden
        all_categories = []
        for trace in data_list:
            chart_type = trace.get('type', 'scatter')
            if chart_type in ['bar', 'histogram', 'funnel', 'waterfall', 'scatter']:
                x_vals = decode_plotly_array(trace.get('x') or trace.get('labels') or trace.get('ids'))
                for val in x_vals:
                    val_str = str(val) if val is not None else ""
                    if val_str and val_str not in all_categories:
                        all_categories.append(val_str)
                        
        has_categorical_x = len(all_categories) > 0
        
        # Contar trazas de barra para calcular desplazamientos (grouped bars)
        bar_traces = [t for t in data_list if t.get('type', 'scatter') in ['bar', 'histogram']]
        total_bars = len(bar_traces)
        bar_width = 0.8 / total_bars if total_bars > 0 else 0.8
        current_bar = 0
            
        for trace in data_list:
            chart_type = trace.get('type', 'scatter')
            
            # Soporte alternativo para Pie, Treemap y Sunburst que usan labels/values en lugar de x/y
            x = decode_plotly_array(trace.get('x') or trace.get('labels') or trace.get('ids'))
            y = decode_plotly_array(trace.get('y') or trace.get('values'))
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
            
            if chart_type in ['bar', 'histogram', 'funnel', 'waterfall']:
                # Agrupar barras lado a lado en lugar de solaparlas
                if has_categorical_x:
                    x_numeric = []
                    y_aligned = []
                    colors_aligned = []
                    for idx, val in enumerate(x):
                        val_str = str(val) if val is not None else ""
                        if val_str in all_categories:
                            x_numeric.append(all_categories.index(val_str))
                            y_aligned.append(y[idx])
                            if isinstance(colors, list) and len(colors) > idx:
                                colors_aligned.append(colors[idx])
                            else:
                                colors_aligned.append(colors)
                    if not x_numeric: continue
                    x_numeric = np.array(x_numeric)
                    y_plot = np.array(y_aligned)
                    colors_plot = colors_aligned if isinstance(colors, list) else colors
                else:
                    x_numeric = np.arange(len(x))
                    y_plot = np.array(y)
                    colors_plot = colors
                
                offset = (current_bar - total_bars/2 + 0.5) * bar_width
                
                bars = ax.bar(x_numeric + offset, y_plot, width=bar_width, label=name, color=colors_plot, alpha=0.85, edgecolor='white', linewidth=0.5)
                
                # Intentar agregar las etiquetas de datos sobre cada barra (Matplotlib 3.4+)
                try:
                    ax.bar_label(bars, padding=3, fontsize=9, fontweight='bold', color='#374151')
                except Exception:
                    pass
                
                current_bar += 1
            elif chart_type in ['pie', 'treemap', 'sunburst']:
                # Agrupar elementos si hay demasiados para que quepan bien en la slide
                if len(y) > 10:
                    sorted_indices = np.argsort(y)[::-1]
                    top_indices = sorted_indices[:9]
                    other_indices = sorted_indices[9:]
                    
                    x_top = [str(x[i]) for i in top_indices]
                    y_top = [y[i] for i in top_indices]
                    
                    y_other = sum(y[i] for i in other_indices)
                    x_top.append("Otros")
                    y_top.append(y_other)
                    
                    x_plot = x_top
                    y_plot = y_top
                else:
                    x_plot = [str(val) for val in x]
                    y_plot = y
                
                ax.pie(y_plot, labels=x_plot, autopct='%1.1f%%', colors=sns.color_palette("viridis", len(y_plot)), textprops={'fontsize': 8})
            else:
                if has_categorical_x:
                    x_numeric = []
                    y_aligned = []
                    for idx, val in enumerate(x):
                        val_str = str(val) if val is not None else ""
                        if val_str in all_categories:
                            x_numeric.append(all_categories.index(val_str))
                            y_aligned.append(y[idx])
                    if not x_numeric: continue
                    x_plot = np.array(x_numeric)
                    y_plot = np.array(y_aligned)
                else:
                    x_plot = x
                    y_plot = y
                
                if isinstance(colors, list): colors = colors[0] if colors else '#2563eb'
                ax.plot(x_plot, y_plot, marker='o', label=name, color=colors, linewidth=2.5, markersize=8)

        # Configuración estética leyendo el layout
        layout = fig_dict.get('layout', {})
        raw_title = layout.get('title', {}).get('text', 'Análisis Estratégico') if isinstance(layout.get('title'), dict) else 'Análisis Estratégico'
        clean_title = re.sub(r'<[^>]*>', '', raw_title) if isinstance(raw_title, str) else 'Análisis Estratégico'
        
        ax.set_title(clean_title, fontsize=16, pad=25, fontweight='bold', color='#111827')
        ax.set_facecolor('#fcfcfc')
        ax.grid(True, axis='y', linestyle='--', alpha=0.4, color='#cbd5e1')
        
        # Configurar las etiquetas del eje X globales si son categóricas
        if has_categorical_x:
            ax.set_xticks(np.arange(len(all_categories)))
            ax.set_xticklabels(all_categories)
        
        # Etiquetas
        xaxis_title = layout.get('xaxis', {}).get('title', {}).get('text', '') if isinstance(layout.get('xaxis'), dict) and isinstance(layout.get('xaxis').get('title'), dict) else ''
        yaxis_title = layout.get('yaxis', {}).get('title', {}).get('text', '') if isinstance(layout.get('yaxis'), dict) and isinstance(layout.get('yaxis').get('title'), dict) else ''
        
        if xaxis_title and isinstance(xaxis_title, str): ax.set_xlabel(re.sub(r'<[^>]*>', '', xaxis_title), fontweight='bold')
        if yaxis_title and isinstance(yaxis_title, str): ax.set_ylabel(re.sub(r'<[^>]*>', '', yaxis_title), fontweight='bold')

        # Rotación inteligente de etiquetas
        plt.xticks(rotation=45, ha='right', fontsize=9)
        
        # Leyenda (siempre mostrarla si hay más de 1 traza o si hay datos etiquetados)
        if len(data_list) > 1 or (data_list and data_list[0].get('name')):
            ax.legend(loc='upper left', bbox_to_anchor=(1, 1), frameon=True, facecolor='white', shadow=True)
            
        plt.tight_layout()
        
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        plt.close()
        
        return img_buffer.getvalue()
    except Exception as ex:
        logger.error("[EXPORT] Fallback crítico Matplotlib: %s", type(ex).__name__)
        return None

def generate_pdf_report(
    user_name: str, 
    messages: list,
    brand_color: str = "#2dd4bf",
    report_org_name: str = "VEKTRA BI",
    report_footer_text: str = "Confidencial - Solo uso interno",
    pdf_orientation: str = "portrait"
):
    """
    Genera un PDF con el historial del chat aplicando el estilo visual corporativo del usuario.
    """
    orient = 'P' if pdf_orientation == 'portrait' else 'L'
    pdf = PremiumBIReport(
        brand_color=brand_color, 
        report_org_name=report_org_name, 
        report_footer_text=report_footer_text, 
        orientation=orient
    )
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font("helvetica", 'B', 20)
    pdf.set_text_color(*pdf.brand_color_rgb)
    pdf.cell(0, 15, txt=f"Reporte de Análisis BI - {report_org_name.upper()}", ln=True, align='C')
    pdf.ln(5)

    for msg in messages:
        role = "Asistente" if msg['role'] == 'assistant' else "Usuario"
        pdf.set_font("helvetica", 'B', 12)
        pdf.set_text_color(*pdf.brand_color_rgb)
        pdf.cell(0, 10, txt=f"{role}:", ln=True)
        
        pdf.set_font("helvetica", size=10)
        pdf.set_text_color(30, 41, 59) # Slate Oscuro
        content = clean_text(msg['content'])
        pdf.multi_cell(0, 6, txt=content)
        pdf.ln(5)
        
        if msg.get('fig'):
            # El reporte simple de chat usa el tema minimalist por defecto
            img_bytes = export_plotly_to_image(msg['fig'], theme="minimalist")
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
    def __init__(self, brand_color: str = "#2dd4bf", report_org_name: str = "VEKTRA BI", report_footer_text: str = "Confidencial - Solo uso interno", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.alias_nb_pages()
        self.brand_color = brand_color
        self.report_org_name = report_org_name
        self.report_footer_text = report_footer_text
        
        # Convertir hex a rgb
        hex_color = brand_color.lstrip('#')
        try:
            self.brand_color_rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except Exception:
            self.brand_color_rgb = (37, 99, 235) # Azul Vektra por defecto
        
    def header(self):
        if self.page_no() == 1:
            return
        # Encabezado con línea fina de acento y texto formal
        self.set_draw_color(*self.brand_color_rgb)
        self.set_line_width(0.5)
        self.line(15, 15, self.w - 15, 15)
        
        self.set_y(8)
        self.set_font('helvetica', 'B', 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f'INFORME DE ANÁLISIS ESTRATÉGICO - {self.report_org_name.upper()}', 0, 1, 'L')
        self.set_y(22)
        
    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_font('helvetica', '', 8)
        self.set_text_color(150, 150, 150)
        
        # Mostrar el pie de página personalizado a la izquierda y el número de página a la derecha
        self.cell(self.w - 50, 10, f'{self.report_footer_text}', 0, 0, 'L')
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

def generate_pro_report(
    title: str, 
    summary: str, 
    user_name: str, 
    items: list,
    brand_color: str = "#2dd4bf",
    report_org_name: str = "VEKTRA BI",
    report_footer_text: str = "Confidencial - Solo uso interno",
    pdf_orientation: str = "portrait",
    pdf_include_data_table: bool = True,
    chart_theme: str = "neon"
):
    """
    Genera un Informe Ejecutivo Profesional con Portada y Resumen Estratégico personalizado.
    """
    # Control de Errores: Reemplazo silencioso de errores de autenticación técnica en el resumen ejecutivo
    error_indicators = ["error de autenticación con gemini", "error de autenticacion", "api key", "autenticación", "gemini api error"]
    if any(ind in summary.lower() for ind in error_indicators):
        summary = "Por favor, configure sus claves API en Ajustes para generar este resumen."

    orient = 'P' if pdf_orientation == 'portrait' else 'L'
    pdf = PremiumBIReport(
        brand_color=brand_color, 
        report_org_name=report_org_name, 
        report_footer_text=report_footer_text, 
        orientation=orient
    )
    pdf.set_margins(15, 20, 15) # Margen izquierdo 15, superior 20, derecho 15
    pdf.set_auto_page_break(auto=True, margin=20)
    
    # --- PORTADA PREMIUM (DARK MODE STYLE) ---
    pdf.add_page()
    w_page = pdf.w
    h_page = pdf.h
    # Fondo oscuro para la portada
    pdf.set_fill_color(15, 15, 15)
    pdf.rect(0, 0, w_page, h_page, "F")
    
    # Acento de color lateral usando el color de marca del usuario
    pdf.set_fill_color(*pdf.brand_color_rgb)
    pdf.rect(0, 0, 5, h_page, "F")
    
    pdf.set_y(h_page * 0.25)
    pdf.set_font("helvetica", 'B', 32 if orient == 'L' else 36)
    pdf.set_text_color(255, 255, 255)
    pdf.multi_cell(0, 18, txt=clean_text(title).upper(), align='L')
    
    pdf.ln(5)
    pdf.set_font("helvetica", 'B', 14)
    pdf.set_text_color(*pdf.brand_color_rgb)
    pdf.cell(0, 10, txt="DIAGNÓSTICO ESTRATÉGICO DE DATOS", ln=True)
    
    pdf.set_y(h_page - 60)
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
    pdf.cell(0, 5, txt=f"{report_org_name.upper()} | {datetime.now().strftime('%Y')}", ln=True, align='R')

    # --- RESUMEN EJECUTIVO ---
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 18)
    pdf.set_text_color(*pdf.brand_color_rgb)
    pdf.cell(0, 15, txt="1. RESUMEN EJECUTIVO", ln=True)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(10)
    
    summary_clean = clean_text(summary)
    paragraphs = [p.strip() for p in summary_clean.split('\n\n') if p.strip()]
    for p in paragraphs:
        # Usar color de acento de marca del usuario
        draw_card(pdf, p, bg_color=(240, 244, 248), border_color=pdf.brand_color_rgb)

    # --- HALLAZGOS Y VISUALIZACIONES ---
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 18)
    pdf.set_text_color(*pdf.brand_color_rgb)
    pdf.cell(0, 15, txt="2. ANÁLISIS DETALLADO", ln=True)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(10)

    for i, item in enumerate(items):
        # Título del hallazgo (usar título si existe, o extraer primera línea)
        pdf.set_font("helvetica", 'B', 14)
        pdf.set_text_color(*pdf.brand_color_rgb)
        
        item_title = item.get('title')
        if not item_title:
            first_line = item['content'].split('\n')[0].strip('# ').strip()
            item_title = first_line if len(first_line) > 5 else f"Análisis de Datos {i+1}"
            
        pdf.multi_cell(0, 10, txt=clean_text(item_title).upper())
        pdf.ln(2)
        
        # Explicación y Tablas
        content = clean_text(item['content'])
        lines = content.split('\n')
        
        elements = []
        current_text = []
        current_table = []
        
        for line in lines:
            line_str = line.strip()
            if line_str.startswith('|') and line_str.endswith('|'):
                if current_text:
                    elements.append(("text", "\n".join(current_text)))
                    current_text = []
                
                cells = [c.strip() for c in line_str.split('|')[1:-1]]
                if all(c.replace('-', '').replace(':', '').strip() == '' for c in cells if c):
                    continue
                current_table.append(cells)
            else:
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
                    pdf.set_font("helvetica", '', 10)
                    pdf.set_text_color(30, 41, 59) # Slate Oscuro
                    
                    if pdf.get_y() + 15 > pdf.page_break_trigger:
                        pdf.add_page()
                        
                    pdf.multi_cell(0, 6, txt=p)
                    pdf.ln(4)
            elif elem_type == "table":
                rows = elem_content
                if not rows:
                    continue
                
                h_table = len(rows) * 6 + 10
                if pdf.get_y() + h_table > pdf.page_break_trigger:
                    pdf.add_page()
                    
                for row_idx, cells in enumerate(rows):
                    col_w = (pdf.w - pdf.l_margin - pdf.r_margin) / max(1, len(cells))
                    
                    if row_idx == 0:
                        pdf.set_font("helvetica", 'B', 8)
                        pdf.set_text_color(255, 255, 255)
                        pdf.set_fill_color(*pdf.brand_color_rgb) # Color de marca
                        pdf.set_draw_color(*pdf.brand_color_rgb)
                    else:
                        pdf.set_font("helvetica", '', 8)
                        pdf.set_text_color(55, 65, 81)
                        if row_idx % 2 == 0:
                            pdf.set_fill_color(243, 244, 246)
                        else:
                            pdf.set_fill_color(255, 255, 255)
                        pdf.set_draw_color(229, 231, 235)
                        
                    for cell in cells:
                        pdf.cell(col_w, 6, txt=cell[:45], border=1, fill=True)
                    pdf.ln(6)
                pdf.ln(4)
        
        # Gráfico
        if item.get('fig'):
            img_bytes = export_plotly_to_image(item['fig'], theme=chart_theme)
            if img_bytes:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(img_bytes)
                    tmp_path = tmp.name
                try:
                    avail_width = pdf.w - pdf.l_margin - pdf.r_margin
                    if pdf.get_y() + 100 > pdf.page_break_trigger:
                        pdf.add_page()
                        
                    pdf.image(tmp_path, x=pdf.l_margin, w=avail_width)
                    pdf.ln(10)
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
        
        if pdf.get_y() > (pdf.h - 80) and i < len(items) - 1:
            pdf.add_page()

    # --- TABLA DE DATOS DETALLADA (OPCIONAL) ---
    if pdf_include_data_table:
        has_table_data = False
        for idx, item in enumerate(items):
            fig = item.get('fig')
            if fig and isinstance(fig, dict) and 'data' in fig:
                traces = fig.get('data', [])
                if traces:
                    trace = traces[0]
                    x_data = decode_plotly_array(trace.get('x') or trace.get('labels') or trace.get('ids'))
                    y_data = decode_plotly_array(trace.get('y') or trace.get('values'))
                    if x_data and y_data:
                        if not has_table_data:
                            pdf.add_page()
                            pdf.set_font("helvetica", 'B', 18)
                            pdf.set_text_color(*pdf.brand_color_rgb)
                            pdf.cell(0, 15, txt="3. APÉNDICE: TABLAS DE DATOS", ln=True)
                            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
                            pdf.ln(10)
                            has_table_data = True
                        
                        pdf.set_font("helvetica", 'B', 12)
                        pdf.set_text_color(*pdf.brand_color_rgb)
                        fig_title = item.get('title') or f"Gráfico {idx+1}"
                        pdf.cell(0, 10, txt=f"Datos tabulares de: {fig_title}", ln=True)
                        pdf.ln(2)
                        
                        pdf.set_font("helvetica", 'B', 8)
                        pdf.set_text_color(255, 255, 255)
                        pdf.set_fill_color(*pdf.brand_color_rgb)
                        pdf.set_draw_color(*pdf.brand_color_rgb)
                        
                        col_w = (pdf.w - pdf.l_margin - pdf.r_margin) / 2
                        pdf.cell(col_w, 6, txt="Dimensión (X)", border=1, fill=True, align='C')
                        pdf.cell(col_w, 6, txt="Métrica (Y)", border=1, fill=True, align='C')
                        pdf.ln(6)
                        
                        pdf.set_font("helvetica", '', 8)
                        pdf.set_text_color(55, 65, 81)
                        for row_idx, (x_val, y_val) in enumerate(zip(x_data[:10], y_data[:10])):
                            if row_idx % 2 == 0:
                                pdf.set_fill_color(243, 244, 246)
                            else:
                                pdf.set_fill_color(255, 255, 255)
                            pdf.set_draw_color(229, 231, 235)
                            
                            pdf.cell(col_w, 6, txt=str(x_val)[:40], border=1, fill=True, align='C')
                            pdf.cell(col_w, 6, txt=str(y_val)[:40], border=1, fill=True, align='C')
                            pdf.ln(6)
                        pdf.ln(6)

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
        "“": '"', "”": '"', "‘": "'", "’": "'",
        "→": "->", "←": "<-", "●": "-", "▪": "-", "■": "-", "◆": "-", "✦": "-", "★": "-"
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

def generate_debate_graph(debate_messages: list):
    """
    Genera un grafo neuronal de debate estilo Obsidian (nodos y aristas conectadas)
    y retorna los bytes de la imagen PNG.
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        
        plt.style.use('fast')
        fig, ax = plt.subplots(figsize=(10, 6.5))
        ax.set_facecolor('#f9fafb')
        fig.patch.set_facecolor('#f9fafb')
        
        # 1. Identificar agentes únicos y recolectar sus roles
        agent_roles = {}
        for m in debate_messages:
            name = m.get('agent_name', '')
            role = m.get('agent_role', '')
            if name and name not in agent_roles:
                agent_roles[name] = role
                
        agents_list = list(agent_roles.keys())
        num_agents = len(agents_list)
        
        if num_agents == 0:
            return None
            
        # Posicionar el Veredicto Central en (0, 0)
        node_positions = {'Veredicto': (0.0, 0.0)}
        
        # Posicionar los agentes circularmente alrededor de (0, 0) con radio R=1.1
        r = 1.1
        for i, agent in enumerate(agents_list):
            theta = 2 * np.pi * i / num_agents
            node_positions[agent] = (r * np.cos(theta), r * np.sin(theta))
            
        # 2. Dibujar Aristas (Líneas de conexión)
        # Conexiones de los agentes hacia el veredicto central (líneas segmentadas púrpuras)
        for agent in agents_list:
            ax.plot([node_positions[agent][0], 0], [node_positions[agent][1], 0], 
                    color='#cbd5e1', linestyle='--', linewidth=1.2, zorder=1)
            
        # Encontrar interacciones en base a menciones y trazar flechas púrpuras
        interactions = []
        for i, msg in enumerate(debate_messages):
            sender = msg.get('agent_name', '')
            content = msg.get('content', '').lower()
            if not sender: continue
            
            # Buscar menciones
            for other in agents_list:
                if other != sender:
                    parts = [p.lower() for p in other.split() if len(p) > 2]
                    for p in parts:
                        if p in content:
                            interactions.append((sender, other))
                            break
                            
        # Si no hay interacciones detectadas, añadir en anillo por defecto
        if not interactions and num_agents > 1:
            for i in range(num_agents):
                interactions.append((agents_list[i], agents_list[(i+1)%num_agents]))
                
        # Dibujar flechas de interacción (curvadas para evitar solapamientos)
        for start, end in set(interactions):
            x1, y1 = node_positions[start]
            x2, y2 = node_positions[end]
            
            # Dibujar una flecha curva usando anotación
            ax.annotate("",
                        xy=(x2, y2), xycoords='data',
                        xytext=(x1, y1), textcoords='data',
                        arrowprops=dict(arrowstyle="-|>", color='#c084fc',
                                        connectionstyle="arc3,rad=0.2",
                                        linewidth=1.5, mutation_scale=12,
                                        shrinkA=18, shrinkB=18),
                        zorder=2)
            
        # 3. Dibujar Nodos (Círculos)
        # Nodo Central (Veredicto)
        ax.scatter(0, 0, s=2600, color='#8b5cf6', edgecolor='#7c3aed', linewidth=2, zorder=3)
        ax.text(0, 0, "VEREDICTO\nENJAMBRE", color='white', fontsize=8, fontweight='bold',
                ha='center', va='center', zorder=4)
        
        # Nodos de Agente
        for agent in agents_list:
            x, y = node_positions[agent]
            ax.scatter(x, y, s=1600, color='white', edgecolor='#a855f7', linewidth=2.2, zorder=3)
            
            initials = "".join([part[0] for part in agent.split() if part])[:2].upper()
            ax.text(x, y, initials, color='#8b5cf6', fontsize=11, fontweight='bold',
                    ha='center', va='center', zorder=4)
            
            # Etiqueta externa (Nombre y Rol del Agente)
            offset_y = -0.25 if y <= 0 else 0.25
            label = f"{agent}\n({agent_roles[agent]})"
            ax.text(x, y + offset_y, label, color='#1e293b', fontsize=7.5, fontweight='bold',
                    ha='center', va='center', zorder=4,
                    bbox=dict(boxstyle="round,pad=0.25", fc='#f8fafc', ec='#ddd6fe', lw=0.8, alpha=0.95))
            
        ax.set_xlim(-1.7, 1.7)
        ax.set_ylim(-1.7, 1.7)
        ax.axis('off')
        
        plt.tight_layout()
        
        import io
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        plt.close()
        
        return img_buffer.getvalue()
    except Exception as e:
        logger.error("[DEBATE_GRAPH] Error en generación de grafo: %s", type(e).__name__)
        return None

class PremiumSimulationReport(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.alias_nb_pages()
        
    def header(self):
        if self.page_no() == 1:
            return
        # Encabezado con línea fina de acento púrpura
        self.set_draw_color(147, 51, 234) # Púrpura de simulación
        self.set_line_width(0.5)
        self.line(15, 15, 195, 15)
        
        self.set_y(8)
        self.set_font('helvetica', 'B', 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, 'ENSAYO DEL FUTURO - PROSPECTIVA Y SIMULACION', 0, 1, 'L')
        self.set_y(22)
        
    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_font('helvetica', '', 8)
        self.set_text_color(150, 150, 150)
        date_str = datetime.now().strftime("%d/%m/%Y")
        
        self.cell(100, 10, f'Vektra BI - Mirofish Lite | {date_str}', 0, 0, 'L')
        self.cell(0, 10, f'Página {self.page_no()} de {{nb}}', 0, 0, 'R')

def generate_simulation_pdf(title: str, hypothesis: str, report: str, debate_messages: list):
    """
    Genera un PDF profesional y estéticamente premium para los Ensayos del Futuro (Simulaciones).
    """
    pdf = PremiumSimulationReport()
    pdf.set_margins(15, 20, 15)
    pdf.set_auto_page_break(auto=True, margin=20)
    
    # --- PORTADA PREMIUM (DARK MODE) ---
    pdf.add_page()
    # Fondo oscuro
    pdf.set_fill_color(20, 15, 30) # Púrpura muy oscuro, casi negro
    pdf.rect(0, 0, 210, 297, "F")
    
    # Acento lateral púrpura brillante
    pdf.set_fill_color(147, 51, 234)
    pdf.rect(0, 0, 6, 297, "F")
    
    # Título del reporte
    pdf.set_y(65)
    pdf.set_font("helvetica", 'B', 28)
    pdf.set_text_color(255, 255, 255)
    pdf.multi_cell(0, 14, txt=clean_text(f"ENSAYO DEL FUTURO:\n{title.upper()}"), align='L')
    
    pdf.ln(6)
    pdf.set_font("helvetica", 'B', 12)
    pdf.set_text_color(168, 85, 247) # Púrpura neón
    pdf.cell(0, 10, txt="DIAGNOSTICO PREDICTIVO & TRAYECTORIA MULTI-AGENTE", ln=True)
    
    # Caja para la hipótesis
    pdf.ln(15)
    pdf.set_font("helvetica", 'B', 10)
    pdf.set_text_color(200, 200, 200)
    pdf.cell(0, 8, txt="HIPOTESIS DE TRABAJO A DEBATIR:", ln=True)
    
    # Dibujar fondo para la hipótesis en la portada
    pdf.set_fill_color(35, 25, 50) # Tarjeta oscura
    pdf.set_draw_color(147, 51, 234) # Borde púrpura
    pdf.set_line_width(0.3)
    
    hyp_clean = clean_text(hypothesis)
    pdf.set_font("helvetica", 'I', 10)
    h_hyp = get_multicell_height(pdf, hyp_clean, 170) + 6
    
    pdf.rect(15, pdf.get_y(), 180, h_hyp, 'FD')
    
    pdf.set_xy(18, pdf.get_y() + 3)
    pdf.set_text_color(220, 210, 235)
    pdf.multi_cell(174, 5, txt=hyp_clean, border=0)
    
    # Datos de autoría y fecha en la parte inferior
    pdf.set_y(240)
    pdf.set_font("helvetica", 'B', 9)
    pdf.set_text_color(168, 85, 247)
    pdf.cell(0, 6, txt="SISTEMA ANALITICO DE INTELIGENCIA DE ENJAMBRE", ln=True, align='R')
    pdf.set_font("helvetica", '', 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, txt="PROCESADO POR VEKTRA BI ENGINE (MIROFISH LITE)", ln=True, align='R')
    pdf.cell(0, 5, txt=f"FECHA DE INFERENCIA: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='R')

    # --- INFORME FINAL (CONCLUSIÓN) ---
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 18)
    pdf.set_text_color(147, 51, 234)
    pdf.cell(0, 15, txt=clean_text("VEREDICTO DEL ENJAMBRE"), ln=True)
    pdf.set_draw_color(147, 51, 234)
    pdf.line(pdf.l_margin, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(5)
    
    # Generar e incrustar el grafo neuronal del debate estilo Obsidian
    graph_bytes = generate_debate_graph(debate_messages)
    if graph_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(graph_bytes)
            tmp_path = tmp.name
        try:
            avail_width = pdf.w - pdf.l_margin - pdf.r_margin
            pdf.image(tmp_path, x=pdf.l_margin, w=avail_width)
            pdf.ln(5)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    # Parsear líneas en elementos de tipo "text" (párrafos) o "table" (lista de celdas)
    report_clean = clean_text(report)
    lines = report_clean.split('\n')
    
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
            # Saltar la línea divisoria de la tabla markdown
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
        
    # Renderizar veredicto
    for elem_type, elem_content in elements:
        if elem_type == "text":
            paragraphs = [p.strip() for p in elem_content.split('\n\n') if p.strip()]
            for p in paragraphs:
                draw_card(pdf, p, bg_color=(250, 245, 255), border_color=(147, 51, 234))
        elif elem_type == "table":
            rows = elem_content
            if not rows:
                continue
            
            # Control preventivo de salto de página para la tabla
            h_table = len(rows) * 6 + 10
            if pdf.get_y() + h_table > pdf.page_break_trigger:
                pdf.add_page()
                
            # Dibujar la tabla con estilo púrpura
            for row_idx, cells in enumerate(rows):
                col_w = (pdf.w - pdf.l_margin - pdf.r_margin) / max(1, len(cells))
                
                if row_idx == 0:
                    # Cabecera púrpura
                    pdf.set_font("helvetica", 'B', 8)
                    pdf.set_text_color(255, 255, 255)
                    pdf.set_fill_color(147, 51, 234) # Púrpura de simulación
                    pdf.set_draw_color(147, 51, 234)
                else:
                    # Filas
                    pdf.set_font("helvetica", '', 8)
                    pdf.set_text_color(55, 65, 81)
                    if row_idx % 2 == 0:
                        pdf.set_fill_color(250, 245, 255) # Zebra striping púrpura claro
                    else:
                        pdf.set_fill_color(255, 255, 255)
                    pdf.set_draw_color(233, 213, 255) # Borde púrpura claro
                    
                for cell in cells:
                    pdf.cell(col_w, 6, txt=cell[:55], border=1, fill=True)
                pdf.ln(6)
            pdf.ln(4)

    # --- REGISTRO DEL DEBATE (APÉNDICE) ---
    if debate_messages:
        pdf.add_page()
        pdf.set_font("helvetica", 'B', 18)
        pdf.set_text_color(147, 51, 234)
        pdf.cell(0, 15, txt=clean_text("APENDICE: REGISTRO DE TRANSCRIPCION"), ln=True)
        pdf.set_draw_color(147, 51, 234)
        pdf.line(pdf.l_margin, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(10)
        
        for msg in debate_messages:
            agent_role = clean_text(msg.get('agent_role', 'Rol'))
            agent_name = clean_text(msg.get('agent_name', 'Agente'))
            content = clean_text(msg.get('content', ''))
            
            title_text = f"[{agent_role}] {agent_name}:"
            
            # Medir la altura total necesaria
            pdf.set_font("helvetica", 'B', 9)
            title_h = 6
            pdf.set_font("helvetica", '', 9)
            body_h = get_multicell_height(pdf, content, 160)
            card_h = max(title_h + body_h + 8, 14) # Mínimo 14mm para contener el avatar de 8mm
            
            if pdf.get_y() + card_h + 2 > pdf.page_break_trigger:
                pdf.add_page()
            
            start_x = pdf.get_x()
            start_y = pdf.get_y()
            avail_w = pdf.w - pdf.l_margin - pdf.r_margin
            
            # 1. Dibujar sombra Drop Shadow (rectángulo desplazado)
            pdf.set_fill_color(240, 238, 245) # Gris/púrpura muy suave
            pdf.rect(start_x + 1, start_y + 1, avail_w, card_h, 'F')
            
            # 2. Dibujar fondo de la tarjeta principal
            pdf.set_fill_color(254, 252, 255) # Fondo blanco-púrpura limpio
            pdf.set_draw_color(233, 213, 255) # Borde púrpura claro
            pdf.rect(start_x, start_y, avail_w, card_h, 'FD')
            
            # Borde izquierdo púrpura más grueso de acento
            pdf.set_fill_color(168, 85, 247)
            pdf.rect(start_x, start_y, 2, card_h, 'F')
            
            # 3. Dibujar Avatar Circular del Agente (diámetro 8mm, centrado en Y)
            avatar_x = start_x + 5
            avatar_y = start_y + (card_h / 2) - 4
            
            pdf.set_fill_color(147, 51, 234)
            pdf.ellipse(avatar_x, avatar_y, 8, 8, 'F')
            
            initial = agent_name[0].upper() if agent_name else "A"
            pdf.set_font("helvetica", 'B', 8)
            pdf.set_text_color(255, 255, 255)
            pdf.set_xy(avatar_x, avatar_y + 1.5)
            pdf.cell(8, 5, txt=initial, border=0, ln=0, align='C')
            
            # 4. Dibujar título (Nombre y Rol del Agente)
            pdf.set_xy(start_x + 15, start_y + 3)
            pdf.set_font("helvetica", 'B', 9)
            pdf.set_text_color(147, 51, 234)
            pdf.cell(160, 5, txt=title_text, ln=True)
            
            # 5. Dibujar contenido del mensaje
            pdf.set_xy(start_x + 15, start_y + 8)
            pdf.set_font("helvetica", '', 9)
            pdf.set_text_color(55, 65, 81)
            pdf.multi_cell(160, 5, txt=content, border=0)
            
            # Posicionar después de la tarjeta
            pdf.set_y(start_y + card_h + 6)

    return pdf.output()
