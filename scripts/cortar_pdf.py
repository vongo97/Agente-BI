import sys
import os

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    print("pypdf no esta instalado")
    sys.exit(1)

input_pdf = r"c:\Users\vongo\OneDrive\Escritorio\Proyectos\Agente-BI\Reportes vektra\Supersociedaees 2024.pdf"
output_pdf = r"c:\Users\vongo\OneDrive\Escritorio\Proyectos\Agente-BI\Reportes vektra\Supersociedades_2024_LinkedIn.pdf"

reader = PdfReader(input_pdf)
writer = PdfWriter()

# Páginas seleccionadas (0-indexed):
# 0: Portada
# 1: Resumen Ejecutivo
# 3: Gráfica Sectores
# 9: Paradoja Volumen (Air-E, Avianca)
# 15: Ecopetrol
# 16: Ecopetrol recomendaciones
pages_to_keep = [0, 1, 3, 9, 15, 16]

for p in pages_to_keep:
    writer.add_page(reader.pages[p])

with open(output_pdf, "wb") as fp:
    writer.write(fp)

print(f"PDF cortado y guardado en: {output_pdf}")
