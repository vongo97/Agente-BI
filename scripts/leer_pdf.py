import fitz

pdf_path = r'c:\Users\vongo\OneDrive\Escritorio\Proyectos\Agente-BI\Reportes vektra\Informe Super sociedades.pdf'
doc = fitz.open(pdf_path)
print(f'Total paginas: {len(doc)}')
text = ''
for page in doc:
    text += page.get_text()

# Save full text to file
with open(r'c:\Users\vongo\OneDrive\Escritorio\Proyectos\Agente-BI\Reportes vektra\informe_texto.txt', 'w', encoding='utf-8') as f:
    f.write(text)

print(text[:8000])
