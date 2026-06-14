---
name: multiplatform-monorepo-sync
description: Guía de sincronización y configuración de arquitecturas monorepo para desarrollo web, móvil y API. Úsalo al configurar dependencias compartidas, generación de clientes y variables globales de localización.
---

# Multiplatform Monorepo & Client Synchronization

Organiza el desarrollo cuando se requiere coordinar múltiples clientes (Web, Android) con un servicio backend centralizado, reduciendo inconsistencias y duplicación de código.

---

## 1. Generación Automática de Clientes desde el Backend

* **OpenAPI / Swagger:** Utiliza el backend (FastAPI, NestJS, Spring Boot, etc.) como fuente única de verdad para las definiciones de las APIs.
* **Cliente TypeScript (Web):** Genera automáticamente clientes de TypeScript y tipos de llamadas de API mediante herramientas como `openapi-typescript` o `swagger-typescript-api`. Esto evita discrepancias de tipos.
* **Cliente Kotlin (Android):** Usa generadores como `openapi-generator-cli` para generar los modelos de datos de Kotlin y llamadas de API de Retrofit a partir del mismo archivo `openapi.json`.

---

## 2. Configuración de Estructuras Monorepo

* **Monorepos (Turborepo, Gradle Multi-project):**
  * Para Javascript/Typescript, organiza carpetas con un espacio de trabajo como:
    ```
    /apps/web (Frontend React/Vite)
    /packages/api-client (Código API auto-generado compartido)
    ```
  * Para proyectos Gradle, puedes integrar submódulos de Android de forma desacoplada compartiendo lógica común mediante scripts de convención.

---

## 3. Sincronización de Recursos de Localización (i18n)

* **Diccionario Único:** Mantén las traducciones de la app en archivos JSON centralizados.
* **Scripts de Sincronización:** Utiliza scripts cortos para convertir los diccionarios de traducción JSON (`en.json`, `es.json`) al formato nativo XML de Android (`strings.xml`) y viceversa, manteniendo la consistencia de textos.
