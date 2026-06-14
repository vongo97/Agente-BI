---
name: vektra-exports-design
description: Pautas de diseño y maquetación visual para exportaciones en PDF y PowerPoint. Úsalo para configurar tipografías, colores, escalas y layouts de reportes.
---

# Vektra Exports Design

Este documento contiene los estándares estéticos y visuales para generar archivos PDF e informes de PowerPoint en Vektra BI.

## Directrices Visuales Generales

1. **Paleta de Colores Corporativos:**
   - **Slate Oscuro (Texto Principal):** `#1e293b` (RGB: 30, 41, 59).
   - **Gris Medio (Texto Secundario):** `#374151` (RGB: 55, 65, 81).
   - **Azul Vektra (Acentos / Bordes):** `#2563eb` (RGB: 37, 99, 235).
   - **Teal Suave (Acentos de Datos):** `#0d9488` (RGB: 13, 148, 136).
   - **Blanco Portada:** `#ffffff` (RGB: 255, 255, 255).

2. **Tipografía Ejecutiva:**
   - Usar `Arial`, `Helvetica` o `Calibri` para todo el contenido y títulos de diapositivas/documentos.

---

## Reglas para PDF (FPDF / FPDF2)

1. **Uso Restringido de Tarjetas (`draw_card`):**
   - **NO** encierres cada párrafo de texto regular en tarjetas separadas.
   - Las tarjetas (`draw_card`) se reservan exclusivamente para:
     * El Resumen Ejecutivo de la sección 1 (tarjeta azul).
     * Mensajes especiales o alertas (tarjeta roja/amarilla).
   - El cuerpo de la Sección 2 ("Análisis Detallado") debe renderizarse como texto corrido plano con espaciado limpio (`pdf.ln(4)`).

2. **Orden de Limpieza de Texto:**
   - Antes de aplicar filtros de expresiones regulares para eliminar encabezados técnicos, se deben limpiar todos los emojis UTF-8 (reemplazándolos por `""`) y los marcadores de formato markdown.

---

## Reglas para PowerPoint (python-pptx)

1. **Layouts de Ancho Dinámico:**
   - **Si la slide tiene un gráfico:** La caja de texto del contenido a la izquierda debe tener un ancho máximo de `Inches(4.5)`.
   - **Si la slide NO tiene gráfico:** La caja de texto debe ensancharse automáticamente a `Inches(11.33)` para equilibrar el balance visual de la diapositiva y evitar zonas vacías.

2. **Contraste de Portada:**
   - Forzar el color de fuente del título y subtítulo a Blanco (`RGBColor(255, 255, 255)`) en la diapositiva de portada (Slide 1) para garantizar su legibilidad sobre fondos oscuros.
