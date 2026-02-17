import os
try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
    from pptx.dml.color import RGBColor
except ImportError:
    Presentation = None

def create_presentation(structured_text, output_path):
    """
    Genera un archivo .pptx a partir de un texto estructurado con '---' como separador de diapositivas.
    Cada diapositiva debe tener un título (H1 o primera línea) y viñetas.
    """
    if Presentation is None:
        return False, "Librería python-pptx no instalada."

    prs = Presentation()
    
    # Slides están separadas por ---
    slides_content = structured_text.split("---")
    
    for content in slides_content:
        content = content.strip()
        if not content:
            continue
            
        lines = content.split("\n")
        title_text = lines[0].replace("#", "").strip()
        body_lines = [l.strip() for l in lines[1:] if l.strip()]
        
        # Crear Slide (Title and Content layout)
        slide_layout = prs.slide_layouts[1] 
        slide = prs.slides.add_slide(slide_layout)
        
        # Configurar Título
        title = slide.shapes.title
        title.text = title_text
        
        # Configurar Cuerpo
        if body_lines:
            tf = slide.placeholders[1].text_frame
            tf.clear() # Limpiar placeholder
            
            for line in body_lines:
                p = tf.add_paragraph()
                # Limpiar viñetas de markdown si existen
                p.text = line.lstrip("- ").lstrip("* ").strip()
                p.level = 0
                if line.startswith("  ") or line.startswith("\t"):
                    p.level = 1

    try:
        prs.save(output_path)
        return True, output_path
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    # Test simple
    test_text = """
    # Ventas Q1
    - Crecimiento del 15%
    - Mercado Latam liderando
    ---
    # Recomendaciones
    - Invertir en Ads
    - Optimizar logística
    """
    create_presentation(test_text, "test_output.pptx")
    print("Test finalizado.")
