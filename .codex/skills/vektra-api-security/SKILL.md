---
name: vektra-api-security
description: Directrices de seguridad de API, CORS, Rate Limiting y aislamiento de ejecución. Úsalo al modificar middleware de FastAPI, enrutadores de API y configuraciones de red.
---

# Vektra API Security

Este documento detalla las directrices de seguridad para proteger los endpoints públicos de la API de Vektra BI contra accesos no autorizados y abusos de cuota.

## Configuración Segura de CORS

1. **Restricción de Orígenes:**
   - **Queda estrictamente prohibido** usar comodines abiertos en producción como `allow_origins=["*"]` o `allow_origin_regex=".*"`.
   - Limita los orígenes CORS únicamente a los dominios autorizados de la empresa (ej: el dominio del frontend en producción y `localhost:3000` / `localhost:5173` en desarrollo).

---

## Limitación de Tasa (Rate Limiting)

1. **Protección de Consumo de Tokens:**
   - Todo endpoint de FastAPI que invoque modelos de LLM (como `/analyze`, `/suggest-questions`, `/export-pptx`, `/visual-summary` o `/detect-anomalies`) debe protegerse mediante límites de velocidad dinámicos usando la librería `slowapi` o Redis.
   - Umbrales por defecto:
     * Peticiones pesadas (`/analyze`, `/visual-summary`): Máximo 5 peticiones por minuto, 30 por hora por IP/Usuario.
     * Peticiones ligeras (`/suggest-questions`): Máximo 10 peticiones por minuto, 60 por hora.

---

## Aislamiento de Ejecución de Código (Sandboxing)

1. **Tratamiento de Datos de Usuario:**
   - El código generado por el LLM debe ejecutarse en un hilo aislado y con límite de tiempo estricto de 10 segundos.
   - Bloquear el acceso a llamadas del sistema (`os.system`, `subprocess`, dunder variables y acceso directo a archivos fuera del directorio temporal).
