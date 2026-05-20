import os
import tempfile
try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
    from pptx.dml.color import RGBColor
except ImportError:
    Presentation = None

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
            print(f"Usando plantilla: {full_template_path}")
            prs = Presentation(full_template_path)
        else:
            print(f"Warning: Template {full_template_path} not found. Using default.")
            prs = Presentation()
            
        # Portada (Modificar primera diapositiva)
        if len(prs.slides) > 0:
            cover = prs.slides[0]
            if cover.shapes.title:
                cover.shapes.title.text = title
            # Buscar placeholders para el resumen
            for shape in cover.placeholders:
                if shape.shape_type == 14 and shape != cover.shapes.title: # Placeholder de texto
                    shape.text = summary
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
            
            # Usar layout 5 (Title Only)
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
                
            # Insertar Texto a la izquierda
            txBox = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(4), Inches(5))
            tf = txBox.text_frame
            tf.word_wrap = True
            
            for line in lines:
                if line.strip().startswith("#"): continue
                if not line.strip(): continue
                p = tf.add_paragraph()
                p.text = line.replace("*", "").strip()
                p.font.size = Pt(12)
                p.font.color.rgb = RGBColor(100, 116, 139) # Slate 500 para legibilidad
                
            # Insertar Gráfico a la derecha
            if fig_data:
                img_bytes = export_plotly_to_image(fig_data)
                if img_bytes:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                        tmp.write(img_bytes)
                        tmp_path = tmp.name
                    try:
                        # Insertar imagen (ancho de 8 pulgadas max para encajar)
                        slide.shapes.add_picture(tmp_path, Inches(4.8), Inches(1.5), width=Inches(8))
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)

        prs.save(output_path)
        return True, output_path
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, str(e)

