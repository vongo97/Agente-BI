---
name: universal-api-mocking-and-testing
description: Estructuras y guías de pruebas y simulación (mocking) de APIs para desarrollo web y móvil. Úsalo al configurar entornos de pruebas unitarias, mocking de red y tests de integración sin depender del backend.
---

# Universal API Mocking & Testing Standards

Garantiza la velocidad de desarrollo y la estabilidad de las pruebas desacoplando las aplicaciones cliente (Web y Móvil) de los servidores reales mediante simulaciones robustas.

---

## 1. Mocking de API en Entornos Web (MSW)

* **Mock Service Worker (MSW):** Intercepta llamadas de red a nivel de red del navegador en lugar de simular llamadas locales. Permite pruebas consistentes en desarrollo y entornos de test (Jest/Vitest).
* **Configuración del Handler:**
  ```javascript
  import { http, HttpResponse } from 'msw'

  export const handlers = [
    http.get('/api/v1/data', () => {
      return HttpResponse.json({ id: 1, name: 'Mock Data' })
    })
  ]
  ```

---

## 2. Mocking de Red en Android (OkHttp Interceptors & MockWebServer)

* **OkHttp MockInterceptor:** Para el desarrollo local rápido sin un backend desplegado, implementa un interceptor OkHttp para devolver respuestas JSON estáticas:
  ```kotlin
  class MockInterceptor : Interceptor {
      override fun intercept(chain: Interceptor.Chain): Response {
          val uri = chain.request().url.toUri()
          val responseString = when {
              uri.path.endsWith("/api/v1/data") -> "{\"id\": 1, \"name\": \"Mock Data\"}"
              else -> "{\"error\": \"Not Found\"}"
          }
          
          return Response.Builder()
              .code(200)
              .message("OK")
              .request(chain.request())
              .protocol(Protocol.HTTP_1_1)
              .body(responseString.toResponseBody("application/json".toMediaTypeOrNull()))
              .addHeader("content-type", "application/json")
              .build()
      }
  }
  ```
* **MockWebServer (OkHttp):** Úsalo en pruebas de integración instrumentadas para simular el comportamiento real de una API REST (respuestas de error 500, demoras de red, etc.).

---

## 3. Pruebas Automatizadas

* **Pruebas en la Web:** Implementa pruebas de UI con Testing Library o Playwright para flujos críticos, verificando cómo reacciona el frontend a los diferentes estados de la API simulados por MSW.
* **Pruebas en Android:** Usa pruebas de Compose UI (`ComposeTestRule`) y simula repositorios usando clases mock/fake para evitar llamadas de red reales en los tests instrumentados de Espresso.
