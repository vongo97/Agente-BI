---
name: vektra-code-verification
description: Pautas de pruebas de resiliencia y verificación sintáctica de código. Úsalo antes de declarar completada cualquier tarea del backend o motor de análisis.
---

# Vektra Code Verification

Este archivo define las reglas de testing e integración para asegurar la robustez de los componentes modificados o nuevos de Vektra BI.

## Checklist de Verificación Obligatoria

1. **Compilación Sintáctica Local:**
   - Antes de dar por terminado cualquier cambio en el backend, se debe ejecutar la compilación sintáctica explícita:
     `.venv\Scripts\python -m py_compile [archivos_modificados]`

2. **Integridad de Importaciones en FastAPI:**
   - Validar que al levantar el servidor o ejecutar scripts de prueba no existan conflictos de rutas circulares o `UnboundLocalError` debidos a variables o importaciones sombreadas.

3. **Pruebas de Resiliencia ante Excepciones:**
   - Simular y verificar escenarios de fallo habituales:
     * **Valores `NaN` o `inf`:** El backend de análisis no debe crashear ni retornar strings del tipo `(nan)` al usuario final.
     * **Claves API Rotadas/Corruptas:** Si `decrypt_key` falla, el sistema debe levantar una excepción HTTP 400 limpia en lugar de pasar claves corruptas a las APIs externas de Gemini o Mistral.
     * **Timeouts de Red:** Validar que los hilos del sandbox interrumpan ejecuciones que superen los 10 segundos.
