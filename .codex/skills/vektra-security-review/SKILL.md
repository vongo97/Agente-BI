---
name: vektra-security-review
description: Revisa y fortalece la seguridad de la API y de los clientes Web/Móvil. Úsalo al modificar o auditar autenticación, autorización, propiedad de endpoints, llaves API, secretos, CORS, límites de tasa, logs, variables de entorno, y seguridad móvil.
---

# Universal Security Review & API Hardening

Aplica esta lista de control de seguridad antes de modificar cualquier código sensible y nuevamente antes de dar por terminada una tarea.

---

## 1. Reglas Generales del Proyecto

* **Identidad y Autenticación:** Trata la identidad del token del backend como la única fuente de verdad. **No confíes** en el `user_id` enviado por el cliente.
* **Propiedad de Datos:** Asegúrate de que cada consulta SQL/Base de datos que afecte a un usuario verifique la propiedad explícitamente (ej: `Model.user_id == authenticated_user`).
* **Protección de Endpoints:** Protege los endpoints destructivos o de configuración mediante autenticación obligatoria y límites de velocidad. Remueve los endpoints exclusivos de desarrollo en producción.
* **Manejo de Secretos:** Nunca registres (logs) llaves API crudas, tokens de portador, cadenas de conexión de base de datos, correos de usuarios en logs de alto volumen, muestras de datos cargados o prompts de LLM que contengan secretos.
* **Configuración Segura:** Requiere variables de entorno explícitas para producción como `AUTH_SECRET`/`NEXTAUTH_SECRET`, `ENCRYPTION_KEY` y orígenes permitidos en CORS.
* **CORS Explícito:** Mantén las políticas CORS restrictivas. No utilices comodines (`*`) con credenciales habilitadas.

---

## 2. Pautas de Seguridad Avanzada (Nivel Profesional)

* **Prevención de Inyección de Fórmulas (CSV Injection):**
  * Al procesar o exportar archivos CSV/Excel, asegúrate de desinfectar y neutralizar cualquier celda que comience con caracteres especiales de fórmula: `=`, `@`, `+`, `-`.
  * Sanitiza estos valores anteponiendo una comilla simple (`'`) para evitar que se ejecuten hojas de cálculo de forma maliciosa.
  * Implementa límites de tamaño de archivo estrictos en el backend y validaciones MIME para evitar ataques de denegación de servicio (como Zip Bombs).

* **Prevención de Cross-Site Scripting (XSS) en Componentes de IA:**
  * Dado que la IA genera Markdown y diagramas de Mermaid dinámicos, el cliente React **debe desinfectar** todas las salidas antes de renderizarlas.
  * Usa librerías como `DOMPurify` o hooks de sanitización de HTML para eliminar etiquetas `<script>`, directivas `javascript:`, e inyecciones de eventos (como `onload` u `onerror`).

* **Almacenamiento Cifrado de Credenciales y Llaves API:**
  * Las llaves API suministradas por los usuarios (como OpenAI, Mistral, etc.) y credenciales de bases de datos externas **deben cifrarse en reposo** en la base de datos utilizando cifrado simétrico (AES-256-GCM) con una clave maestra del servidor (`ENCRYPTION_KEY`).
  * Nunca transmitas estas llaves API en texto plano repetidamente a través de la red si ya se encuentran almacenadas.

* **Enmascaramiento de Errores y Stack Traces (Error Hardening):**
  * En producción, está **estrictamente prohibido** exponer stack traces detallados de Python, FastAPI o Next.js al cliente final.
  * Implementa un manejador global de excepciones (Exception Handler) que capture excepciones no controladas en el backend, registre el error real en logs seguros internos, y devuelva al cliente un mensaje genérico junto con un ID de error único (ej. `{"error": "Fallo interno del servidor", "error_id": "ERR-12345"}`).

* **Mitigación de Inyección SQL en Consultas Generadas por IA:**
  * Al procesar consultas de bases de datos generadas dinámicamente por la IA o los usuarios, se debe utilizar parametrización estricta (Prepared Statements) o el motor ORM (SQLAlchemy) con condiciones tipadas.
  * Queda **prohibida** la concatenación directa de entradas de usuario en strings SQL de ejecución.

---

## 3. Seguridad Específica para Clientes Móviles e Integración de Red

* **Autenticación Segura (OAuth2 con PKCE):** 
  * Para las aplicaciones móviles nativas (Android), el flujo de autenticación debe implementar OAuth2 con **Proof Key for Code Exchange (PKCE)** para evitar la interceptación del código de autorización por parte de apps maliciosas en el dispositivo.
* **Seguridad CORS y User-Agents:**
  * Si la app Android realiza peticiones a la API del backend, el backend debe estar configurado para admitir llamadas seguras desde orígenes móviles específicos (o manejar tokens Web seguros) sin debilitar las políticas CORS de navegadores web.
* **Inspección de Certificados (SSL Pinning):**
  * Implementa SSL Pinning en los clientes móviles Android (a través del cliente `OkHttpClient` o configuraciones del sistema de red) para bloquear ataques de intermediarios (MITM) en redes públicas.

---

## 4. Flujo de Trabajo para Auditoría de Código

1. **Identificar Fronteras de Confianza:** Define claramente las interacciones entre navegador, NextAuth, API de FastAPI, base de datos, sistemas de archivos temporales, APIs de LLM y el worker de sandbox aislado.
2. **Trazabilidad de Identidad:** Rastrea cómo fluye la sesión del usuario desde `client/src/auth.ts` hasta los middlewares de FastAPI.
3. **Validación de Entradas:** Comprueba que no haya suplantación de identidad en parámetros, exposición de secretos en URLs o manipulación de rutas de archivos (`Path Traversal`).
4. **Pruebas de Seguridad:** Escribe o ejecuta tests específicos para validar que los endpoints de borrado u obtención de reportes fallen adecuadamente con tokens alterados o usuarios diferentes.
