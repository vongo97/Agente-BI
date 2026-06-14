import os
import tempfile
import logging
try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
    from pptx.dml.color import RGBColor
except ImportError:
    Presentation = None

logger = logging.getLogger(__name__)
from src.utils.exporter import export_plotly_to_image, clean_text

def summarize_text_for_slide(text, api_key=None):
    """
    Sintetiza el análisis largo a viñetas ejecutivas cortas usando Gemini,
    o aplica un fallback algorítmico si no hay clave de API.
    """
    if not api_key:
        return fallback_summarization(text)

    prompt = f"""
    Eres un Consultor de BI experto en presentaciones ejecutivas de nivel Directivo (McKinsey/Gartner).
    Tu misión es transformar el siguiente análisis detallado en puntos clave de impacto para una sola diapositiva.

    REGLAS ESTRICTAS:
    1. Devuelve un máximo de 3 a 4 puntos clave (bullets).
    2. Cada punto clave debe ser conciso, potente y tener un máximo de 15 palabras.
    3. Destaca la métrica numérica clave y el impacto comercial.
    4. Cada punto debe iniciar con una viñeta simple "-" (guion).
    5. NO incluyas introducciones, títulos, ni notas. Solo las viñetas.

    ANÁLISIS A SINTETIZAR:
    {text}
    """
    try:
        from src.engine.bi_analyst import generate_ai_content
        summary_raw = generate_ai_content(prompt, api_key, provider="gemini", temperature=0.3, model_level="ANALYTICS")
        if summary_raw and "⚠️" not in summary_raw:
            bullets = [b.strip().lstrip("-*• ").strip() for b in summary_raw.split("\n") if b.strip()]
            bullets = [b for b in bullets if len(b) > 5]
            if len(bullets) >= 2:
                return bullets
    except Exception as e:
        logger.warning("Fallo en síntesis inteligente para diapositiva: %s. Usando fallback.", e)

    return fallback_summarization(text)

def fallback_summarization(text):
    """Extrae las oraciones de mayor impacto de manera determinista."""
    import re
    clean_lines = [line.strip() for line in text.split("\n") if line.strip() and not line.strip().startswith("#") and "|" not in line]
    sentences = []
    for line in clean_lines:
        parts = re.split(r'\.\s+', line)
        for p in parts:
            p_clean = p.strip().rstrip(".")
            if len(p_clean) > 20:
                sentences.append(p_clean)
    return sentences[:3]

def create_presentation(title, summary, items, output_path, template_path="templates/template_vektra_general.pptx", api_key=None):
    """
    Genera un archivo .pptx a partir de hallazgos usando una plantilla maestra.
    """
    if Presentation is None:
        return False, "Librería python-pptx no instalada."

    try:
        # Resolver ruta absoluta del template
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        full_template_path = os.path.join(base_dir, template_path)
        
        if os.path.exists(full_template_path):
            logger.debug("Usando plantilla PPTX: %s", os.path.basename(full_template_path))
            prs = Presentation(full_template_path)
        else:
            logger.warning("Plantilla PPTX no encontrada. Usando presentación vacía.")
            prs = Presentation()
            
        # Eliminar diapositivas sobrantes de la plantilla (conservar solo la 0 de portada)
        while len(prs.slides) > 1:
            rId = prs.slides._sldIdLst[1].rId
            prs.part.drop_rel(rId)
            del prs.slides._sldIdLst[1]

        # Forzar tamaño 16:9 Widescreen para dar protagonismo a los gráficos BI
        prs.slide_width = Inches(13.33)
        prs.slide_height = Inches(7.5)
            
        # Portada (Modificar primera diapositiva)
        if len(prs.slides) > 0:
            cover = prs.slides[0]
            # Establecer fondo oscuro Slate 900 en la portada
            cover.background.fill.solid()
            cover.background.fill.fore_color.rgb = RGBColor(15, 23, 42)
            
            # Añadir barra lateral decorativa en Azul Vektra
            from pptx.enum.shapes import MSO_SHAPE
            accent_bar = cover.shapes.add_shape(MSO_SHAPE.RECTANGLE, left=0, top=0, width=Inches(0.4), height=prs.slide_height)
            accent_bar.fill.solid()
            accent_bar.fill.fore_color.rgb = RGBColor(37, 99, 235)
            accent_bar.line.fill.background() # Quitar contorno
            
            # Truncar resumen si supera los 250 caracteres
            truncated_summary = summary
            if len(truncated_summary) > 250:
                truncated_summary = truncated_summary[:247] + "..."

            if cover.shapes.title:
                cover.shapes.title.text = title
                # Forzar color de fuente a Blanco recorriendo párrafos
                for paragraph in cover.shapes.title.text_frame.paragraphs:
                    paragraph.font.color.rgb = RGBColor(255, 255, 255)
                    paragraph.font.name = "Arial"
                    if len(title) > 30:
                        paragraph.font.size = Pt(36)
                        
            # Buscar placeholders para el resumen
            for shape in cover.placeholders:
                if shape.shape_type == 14 and shape != cover.shapes.title: # Placeholder de texto
                    shape.text = truncated_summary
                    for paragraph in shape.text_frame.paragraphs:
                        paragraph.font.name = "Arial"
                        paragraph.font.size = Pt(14)
                        paragraph.font.color.rgb = RGBColor(255, 255, 255) # Forzar blanco
                    break
        else:
            # Crear portada por defecto si la plantilla está totalmente vacía
            slide_layout = prs.slide_layouts[0] 
            slide = prs.slides.add_slide(slide_layout)
            
            # Establecer fondo oscuro Slate 900
            slide.background.fill.solid()
            slide.background.fill.fore_color.rgb = RGBColor(15, 23, 42)
            
            from pptx.enum.shapes import MSO_SHAPE
            accent_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left=0, top=0, width=Inches(0.4), height=prs.slide_height)
            accent_bar.fill.solid()
            accent_bar.fill.fore_color.rgb = RGBColor(37, 99, 235)
            accent_bar.line.fill.background()
            
            truncated_summary = summary
            if len(truncated_summary) > 250:
                truncated_summary = truncated_summary[:247] + "..."

            slide.shapes.title.text = title
            for paragraph in slide.shapes.title.text_frame.paragraphs:
                paragraph.font.name = "Arial"
                paragraph.font.color.rgb = RGBColor(255, 255, 255)
                
            slide.placeholders[1].text = truncated_summary
            for paragraph in slide.placeholders[1].text_frame.paragraphs:
                paragraph.font.name = "Arial"
                paragraph.font.color.rgb = RGBColor(255, 255, 255)

        # Forzar color de fuente a Blanco en toda la portada (Slide 1) para garantizar legibilidad
        if len(prs.slides) > 0:
            cover = prs.slides[0]
            for shape in cover.shapes:
                if shape.has_text_frame and shape.name != "accent_bar":
                    for paragraph in shape.text_frame.paragraphs:
                        paragraph.font.color.rgb = RGBColor(255, 255, 255)

        # Diapositivas de contenido
        for item in items:
            content_text = item.get("content", "")
            fig_data = item.get("fig")
            
            # Usar layout 5 (Title Only) o el 1 (Title and Content)
            layout = prs.slide_layouts[5] if len(prs.slide_layouts) > 5 else prs.slide_layouts[1]
            slide = prs.slides.add_slide(layout)
            
            # Establecer fondo claro Slate 50 en la diapositiva de contenido
            slide.background.fill.solid()
            slide.background.fill.fore_color.rgb = RGBColor(248, 250, 252)
            
            # Añadir línea decorativa horizontal en Azul Vektra debajo del encabezado
            from pptx.enum.shapes import MSO_SHAPE
            header_line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left=Inches(0.5), top=Inches(1.6), width=Inches(12.33), height=Inches(0.03))
            header_line.fill.solid()
            header_line.fill.fore_color.rgb = RGBColor(37, 99, 235)
            header_line.line.fill.background() # Quitar borde
            
            # Añadir pie de diapositiva discreto de marca corporativa
            footer_box = slide.shapes.add_textbox(Inches(0.5), Inches(7.0), Inches(12.33), Inches(0.4))
            tf_footer = footer_box.text_frame
            tf_footer.word_wrap = True
            p_foot = tf_footer.paragraphs[0]
            p_foot.text = "VEKTRA BI ENGINE | DIAGNÓSTICO ESTRATÉGICO"
            p_foot.font.name = "Arial"
            p_foot.font.size = Pt(8)
            p_foot.font.color.rgb = RGBColor(148, 163, 184) # Slate 400
            
            # Extraer y limpiar título del contenido
            lines = content_text.split("\n")
            slide_title = "Hallazgo Estratégico"
            for line in lines:
                if line.strip().startswith("#"):
                    slide_title = clean_text(line.replace("#", "").strip())
                    break
                    
            # Determinar ancho de la caja de texto de forma dinámica (12.33 sin gráfico, 4.5 con gráfico)
            has_chart = bool(fig_data)
            textbox_width = Inches(12.33) if not has_chart else Inches(4.5)
            
            if slide.shapes.title:
                slide.shapes.title.text = slide_title
                # IMPORTANTE: Forzar el tamaño de la fuente, nombre y color Slate 800
                for paragraph in slide.shapes.title.text_frame.paragraphs:
                    paragraph.font.name = "Arial"
                    paragraph.font.size = Pt(24)
                    paragraph.font.bold = True
                    paragraph.font.color.rgb = RGBColor(30, 41, 59) # Slate Oscuro
                
            # Insertar Texto (Ajustado dinámicamente con margen de seguridad superior top=2.0)
            txBox = slide.shapes.add_textbox(Inches(0.5), Inches(2.0), textbox_width, Inches(4.8))
            tf = txBox.text_frame
            tf.word_wrap = True
            
            # Sintetizar el contenido usando el Sintetizador Ejecutivo Híbrido
            bullets = summarize_text_for_slide(content_text, api_key)
            
            # Tamaño de fuente estándar para viñetas ejecutivas
            font_size = Pt(13) if len(bullets) <= 3 else Pt(11.5)
            
            first_p = True
            for b_text in bullets:
                if first_p:
                    p = tf.paragraphs[0]
                    first_p = False
                else:
                    p = tf.add_paragraph()
                    
                p.font.name = "Arial"
                p.font.size = font_size
                p.font.color.rgb = RGBColor(75, 85, 99) # Slate Gris Medio (#4b5563) para el cuerpo
                p.space_after = Pt(8) # Espacio elegante entre viñetas
                p.text = "• " + clean_text(b_text).strip()
                
            # Insertar Gráfico a la derecha (balanceado vertical y horizontalmente)
            if fig_data:
                img_bytes = export_plotly_to_image(fig_data)
                if img_bytes:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                        tmp.write(img_bytes)
                        tmp_path = tmp.name
                    try:
                        # Insertar imagen alineada con el texto en posición left=5.3 (ancho 7.5)
                        slide.shapes.add_picture(tmp_path, Inches(5.3), Inches(2.0), width=Inches(7.5))
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)

        prs.save(output_path)
        return True, output_path
    except Exception as e:
        is_render = os.getenv("RENDER", "false").lower() == "true"
        if not is_render:
            logger.exception("Fallo en generación PPTX: %s", type(e).__name__)
        else:
            logger.error("Fallo en generación PPTX: %s", type(e).__name__)
        return False, f"Fallo en generación PPTX: {type(e).__name__}"

