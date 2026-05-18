import io
import json
import plotly.io as pio
import plotly.graph_objects as go
from fpdf import FPDF
import tempfile
import os
import re
from datetime import datetime

def export_plotly_to_image(fig_data: any, format: str = "png"):
    """
    Convierte un objeto/dict de Plotly a bytes de imagen (PNG).
    """
    try:
        # Si ya es un dict, no necesitamos json.loads
        fig_dict = fig_data
        if isinstance(fig_data, str):
            fig_dict = json.loads(fig_data)
        
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
            font={'color': '#111827', 'family': 'Helvetica', 'size': 12},
            margin=dict(l=50, r=50, t=80, b=50),
            width=800,
            height=500
        )
        
        # Configurar ejes para que se vean bien en papel
        fig.update_xaxes(gridcolor='#e5e7eb', zerolinecolor='#d1d5db')
        fig.update_yaxes(gridcolor='#e5e7eb', zerolinecolor='#d1d5db')

        # Intentar exportar usando kaleido
        print(f"[DEBUG EXPORT] Intentando kaleido para gráfico con {len(fig.data)} trazas...")
        img_bytes = pio.to_image(fig, format=format, engine="kaleido", scale=4)
        print(f"[DEBUG EXPORT] EXITO: {len(img_bytes)} bytes generados con Kaleido")
        return img_bytes
    except Exception as e:
        print(f"[WARNING EXPORT] Kaleido falló: {str(e)}. Intentando Fallback con Matplotlib...")
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
            print(f"[ERROR EXPORT] Fallo decodificando bdata: {e}")
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
            ax.legend(frameon=True, facecolor='white', shadow=True)
            
        plt.tight_layout()
        
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=400, bbox_inches='tight')
        plt.close()
        
        return img_buffer.getvalue()
    except Exception as ex:
        print(f"[ERROR EXPORT] Fallback crítico: {str(ex)}")
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

def generate_pro_report(title: str, summary: str, user_name: str, items: list):
    """
    Genera un Informe Ejecutivo Profesional con Portada y Resumen Estratégico.
    """
    pdf = FPDF()
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
    pdf.multi_cell(0, 18, txt=title.upper(), align='L')
    
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
    
    # Formatear el nombre por si es un correo
    formatted_name = user_name
    if "@" in formatted_name:
        formatted_name = formatted_name.split("@")[0]
        formatted_name = re.sub(r'\d+$', '', formatted_name)
        formatted_name = formatted_name.replace(".", " ").replace("_", " ")
        
    pdf.cell(0, 10, txt=formatted_name.upper(), ln=True, align='R')
    
    pdf.ln(5)
    pdf.set_font("helvetica", 'B', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, txt=f"VEKTRA BI ENGINE | {datetime.now().strftime('%Y')}", ln=True, align='R')

    # --- RESUMEN EJECUTIVO ---
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 18)
    pdf.set_text_color(20, 80, 160)
    pdf.cell(0, 15, txt="1. RESUMEN EJECUTIVO", ln=True)
    pdf.line(pdf.l_margin, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(10)
    
    pdf.set_font("helvetica", '', 11)
    pdf.set_text_color(0, 0, 0)
    summary_clean = clean_text(summary)
    pdf.multi_cell(0, 7, txt=summary_clean)

    # --- HALLAZGOS Y VISUALIZACIONES ---
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 18)
    pdf.set_text_color(20, 80, 160)
    pdf.cell(0, 15, txt="2. ANÁLISIS DETALLADO", ln=True)
    pdf.line(pdf.l_margin, pdf.get_y(), 200, pdf.get_y())
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
        
        # Explicación (Limpia de Markdown)
        pdf.set_font("helvetica", '', 10)
        pdf.set_text_color(50, 50, 50)
        content = clean_text(item['content'])
        pdf.multi_cell(0, 6, txt=content)
        pdf.ln(5)
        
        # Gráfico
        if item.get('fig'):
            img_bytes = export_plotly_to_image(item['fig'])
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
    """Limpia el texto eliminando artefactos de markdown y caracteres no soportados por latin-1"""
    if not text: return ""
    
    # 1. Eliminar artefactos de Markdown comunes
    import re
    # Eliminar #, ##, ### del inicio de las líneas
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    # Eliminar ** (negritas)
    text = text.replace("**", "")
    # Eliminar * (itálicas o bullets)
    text = text.replace("* ", " - ")
    
    # 2. Reemplazar caracteres especiales por equivalentes seguros
    replacements = {
        "•": "-", "—": "-", "–": "-",
        "“": '"', "”": '"', "‘": "'", "’": "'",
        "💡": "INFO:", "⚠️": "ATENCION:", "🚀": "TIP:", 
        "🔍": "ANALISIS:", "🎯": "OBJETIVO:", "⚡": "ALERTA:",
        "🏁": "ACCION:", "📊": "DATA:"
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
        
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
