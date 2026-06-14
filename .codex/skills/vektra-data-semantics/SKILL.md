---
name: vektra-data-semantics
description: Traducción y mapeo semántico de variables y datos técnicos a terminología formal en español. Úsalo cuando el modelo genere explicaciones de negocio basadas en datos de tablas.
---

# Vektra Data Semantics

Este archivo establece las reglas semánticas para asegurar que el sistema de IA traduzca de forma transparente los nombres técnicos de columnas a un español de negocios formal.

## Reglas de Traducción de Variables

1. **Prohibición de Slugs en Narrativas:**
   - Queda estrictamente prohibido que el usuario final visualice en el chat, en los PDFs o en los PowerPoint nombres de variables técnicos, slugs de bases de datos o campos con guiones bajos (ej: `num_empresas`, `ingreso_total_fmt`, `categoria_salud`, `porcentaje_nacional`).

2. **Traducción Contextual Obligatoria:**
   - La IA debe mapear dinámicamente cada slug a un término formal en español de negocios al redactar la narrativa:
     * `num_empresas` ➔ "Número de empresas" / "Total de organizaciones"
     * `ingreso_total_fmt` o `ingresos` ➔ "Ingresos totales" / "Facturación total"
     * `categoria_salud` ➔ "Estado de salud financiera"
     * `departamento` ➔ "Región" / "Ubicación geográfica"
     * `porcentaje_nacional` ➔ "Aporte porcentual nacional"

3. **Fidelidad Numérica y Factual:**
   - La traducción de nombres técnicos a lenguaje humano **NO** debe alterar bajo ninguna circunstancia los valores numéricos calculados ni cruzar variables incorrectamente.
