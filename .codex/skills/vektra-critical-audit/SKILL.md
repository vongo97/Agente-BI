---
name: vektra-critical-audit
description: Auditoría crítica y rigurosa de propuestas de implementación y planes. Úsalo para definir el estándar de revisión que Antigravity debe seguir antes de proponer código o aceptar sugerencias del programador.
---

# Vektra Critical Audit

Este archivo define las reglas inquebrantables de revisión que el copiloto de IA (Antigravity) debe seguir para evitar aprobaciones automáticas ("rubber-stamping") y asegurar la máxima calidad.

## Reglas de Fricción Técnica

1. **Revisión Destructiva Obligatoria:**
   - Ante cualquier plan de implementación o solicitud del usuario/desarrollador, **NO apruebes de inmediato**.
   - Debes identificar y documentar explícitamente al menos **2 posibles fallos lógicos o vulnerabilidades**, **2 casos extremos (edge-cases)** y **1 sugerencia de optimización de diseño/UX**.

2. **Filtro Semántico de Datos (Anti-Slugs):**
   - Asegurar que el plan de prompts de la IA obligue a mapear nombres de columnas de bases de datos a términos humanos del español de negocios (ej. de `ingreso_total_fmt` a "Ingresos Totales").

3. **Verificación Estética:**
   - Comprobar que cualquier diseño visual de salida cumpla estrictamente con la simplicidad, sobriedad y la paleta de colores corporativos de Vektra BI.

4. **Validación de Resiliencia:**
   - Validar que el código propuesto maneje correctamente estados vacíos, nulos (`NaN`), timeouts e inestabilidades de red.
