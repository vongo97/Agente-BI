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
from src.utils.exporter import export_plotly_to_image

def create_presentation(title, summary, items, output_path, template_path="templates/template_vektra_general.pptx"):
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
            
        # Forzar tamaño 16:9 Widescreen para dar protagonismo a los gráficos BI
        prs.slide_width = Inches(13.33)
        prs.slide_height = Inches(7.5)
            
        # Portada (Modificar primera diapositiva)
        if len(prs.slides) > 0:
            cover = prs.slides[0]
            if cover.shapes.title:
                cover.shapes.title.text = title
                # Bajar tamaño si el título es muy largo
                if len(title) > 30 and len(cover.shapes.title.text_frame.paragraphs) > 0:
                    cover.shapes.title.text_frame.paragraphs[0].font.size = Pt(36)
            # Buscar placeholders para el resumen
            for shape in cover.placeholders:
                if shape.shape_type == 14 and shape != cover.shapes.title: # Placeholder de texto
                    shape.text = summary
                    if len(shape.text_frame.paragraphs) > 0:
                        shape.text_frame.paragraphs[0].font.size = Pt(14)
                    break
        else:
            # Crear portada por defecto si la plantilla está totalmente vacía
            slide_layout = prs.slide_layouts[0] 
            slide = prs.slides.add_slide(slide_layout)
            slide.shapes.title.text = title
            slide.placeholders[1].text = summary

        # Diapositivas de contenido
        for item in items:
            content_text = item.get("content", "")
            fig_data = item.get("fig")
            
            # Usar layout 5 (Title Only) o el 1 (Title and Content)
            layout = prs.slide_layouts[5] if len(prs.slide_layouts) > 5 else prs.slide_layouts[1]
            slide = prs.slides.add_slide(layout)
            
            # Extraer título del contenido
            lines = content_text.split("\n")
            slide_title = "Hallazgo Estratégico"
            for line in lines:
                if line.strip().startswith("#"):
                    slide_title = line.replace("#", "").strip()
                    break
                    
            if slide.shapes.title:
                slide.shapes.title.text = slide_title
                # IMPORTANTE: Forzar el tamaño de la fuente para que no aplaste el resto (28 Pt)
                for paragraph in slide.shapes.title.text_frame.paragraphs:
                    paragraph.font.size = Pt(28)
                
            # Insertar Texto a la izquierda (Ajustado al formato 16:9)
            txBox = slide.shapes.add_textbox(Inches(0.5), Inches(2.2), Inches(4.5), Inches(4.8))
            tf = txBox.text_frame
            tf.word_wrap = True
            
            # Calcular longitud para hacer el texto responsivo
            texto_total_longitud = sum(len(line) for line in lines if not line.strip().startswith("#"))
            font_size = Pt(13)
            if texto_total_longitud > 350:
                font_size = Pt(11)
            elif texto_total_longitud > 550:
                font_size = Pt(9.5)
            
            for line in lines:
                if line.strip().startswith("#"): continue
                if not line.strip(): continue
                p = tf.add_paragraph()
                p.text = "• " + line.replace("**", "").replace("*", "").strip()
                p.font.size = font_size
                p.font.color.rgb = RGBColor(100, 116, 139) # Slate 500 para legibilidad
                
            # Insertar Gráfico a la derecha
            if fig_data:
                img_bytes = export_plotly_to_image(fig_data)
                if img_bytes:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                        tmp.write(img_bytes)
                        tmp_path = tmp.name
                    try:
                        # Insertar imagen alineada con el texto en posición 5.2 (ancho 8)
                        slide.shapes.add_picture(tmp_path, Inches(5.2), Inches(2.2), width=Inches(8))
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

