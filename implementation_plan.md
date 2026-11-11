# Implementation Plan — Lista Roja (Problemas Conocidos Abiertos)

**Proyecto:** Agente-BI / Vektra BI  
**Fecha:** 2026-10-22  
**Estado:** Pendiente de aprobación del usuario  
**Autor:** Antigravity

---

## Contexto

Este plan agrupa los problemas conocidos abiertos (`docs/PROBLEMAS_CONOCIDOS.md`) por prioridad.  
Ningún cambio se aplicará sin tu aprobación explícita (`Proceed`) sobre cada fase o ítem.

Problemas ya cerrados en esta sesión (no están en este plan): P-27, P-03, P-05, P-10, P-13, P-16, P-55.

---

## Fase 1 — Seguridad y estabilidad crítica (recomendada primero)

| ID | Problema | Archivos | Cambio necesario | Beneficio |
|---|---|---|---|---|
| **P-07** | CSP permisiva (`unsafe-inline`, `unsafe-eval`, `connect-src ws: wss:`, sin `frame-ancestors`) | `client/next.config.ts:19-28` | Reemplazar `unsafe-inline`/`unsafe-eval` por nonces o hashes; restringir `connect-src` a los orígenes del backend y Supabase; añadir `frame-ancestors 'none'`. | Reduce superficie de XSS e inyección de contenido malicioso. |
| **P-08** | Capa de red sin timeout, `AbortController`, retry ni reacción a 401/403 | `client/src/lib/api.ts:15-32` | Envolver `securedFetch` con `AbortController` (timeout 30s), retry exponencial (máx. 2) y mapear 401/403 a cierre de sesión + redirect `/login`. | La UI no se queda colgada; errores de auth se manejan limpiamente. |
| **P-11** | Original escrito en claro en `.tmp` antes de cifrar; sin mitigación de zip-bomb | `server/src/routers/data.py:110-192` | Cifrar en memoria y escribir directo al destino final sin `.tmp` intermedio claro; limitar filas/columnas y tamaño de archivo en upload (zip-bomb). | Evita fuga de datos sin cifrar y ataques por descompresión descontrolada. |
| **P-12** | `str(e)` de excepciones internas persistido y devuelto al cliente | `server/src/routers/simulation.py:139,458,461` (y similares) | Reemplazar `str(e)` por mensajes genéricos saneados + `X-Request-Id`; registrar detalle solo en logs internos. | No se filtran rutas, credenciales parciales ni stack traces al cliente. |
| **P-15** | Sin allowlist ni middleware en cliente: cualquier cuenta Google entra y queda inservible (403) | `client/src/auth.ts:7-30`, `app/page.tsx:20-24` | Añadir allowlist de correos autorizados en middleware/cliente; si el email no está en la lista, bloquear acceso con mensaje claro. | Solo usuarios autorizados usan la app; evita confusiones con cuentas ajenas. |

**Criterio de cierre Fase 1:** `tsc --noEmit` limpio, `npm run build` OK, y tests de seguridad nuevos pasan.

---

## Fase 2 — Correctitud de datos y UX

| ID | Problema | Archivos | Cambio necesario | Beneficio |
|---|---|---|---|---|
| **P-14** | El modelo mostrado en el selector no es el que usa el backend | `client/src/components/ProviderKeysPanel.tsx:43-54,130`, `client/src/context/DashboardContext.tsx:146-167` | Sincronizar el proveedor mostrado con el que realmente se resuelve en `resolve_keys()`; mostrar el modelo efectivo. | El usuario no ve un modelo distinto al que realmente ejecuta. |
| **P-26** | "Guardar Cambios" en Ajustes no guarda nada | `client/src/components/SettingsView.tsx:72-76` | Conectar el botón a la persistencia real de preferencias (o deshabilitarlo/eliminarlo hasta que funcione). | No hay expectativa falsa de que los cambios se guardaron. |
| **P-34** | Sesión guardada por usuario (sin `chat_id`) → conversaciones se pisan | `server/src/utils/common.py:234-320,455-490` | `ensure_user_session` debe aislar por `user_id + chat_id`; test de dos conversaciones simultáneas que verifique que no se mezclan. | Dos abiertas al mismo tiempo no se sobrescriben. |
| **P-35** | `data_store` global en memoria sin límite ni TTL | `server/src/utils/common.py` | Añadir LRU o TTL con tamaño máximo; test de crecimiento que no exceda el límite. | Evita OOM en Render free (512 MB) con muchas conversaciones. |
| **P-27** | (Ya cerrado) — Fuentes con alcance por conversación | — | Ya implementado en esta sesión. | — |

**Criterio de cierre Fase 2:** tests de aislamiento de sesiones y TTL pasan; `tsc` y `build` OK.

---

## Fase 3 — Funcionalidad y deuda menor

| ID | Problema | Archivos | Cambio necesario | Beneficio |
|---|---|---|---|---|
| **P-37** | `generate_auto_dashboard` es stub con TODO | `server/src/engine/bi_analyst.py:634` | Implementar generación real de métricas y gráficos a partir del dataset, o devolver `501` explícito y ocultar el botón. | El botón "Auto-Dashboard" deja de mostrar "0 gráficos, 0 métricas". |
| **P-38** | Layout de dashboard desde `localStorage` sin validar; `any` en simulación | `client/src/components/DashboardView.tsx:222-229`, `client/src/components/SimulationSandbox.tsx:13` | Validar esquema de layout al leer `localStorage`; reemplazar `any` por tipos reales. | Evita errores de hidratación y layouts rotos. |
| **P-39** | Estado `pending` se etiqueta como "Fallo" | `client/src/components/SimHistory.tsx:42` | Mapear estados correctamente: `pending` ≠ fallo. | El usuario ve el estado real de sus simulaciones. |
| **P-40** | Texto de 8-10 px y sidebar fija en móvil | `client/src/components/SimHistory.tsx:12` y varios | Mínimo 12 px; sidebar responsive en móvil. | Accesibilidad y usabilidad en móviles. |
| **P-41** | 3 tests backend fallando (`test_exports.py`, `test_simulation.py`) | `server/tests/test_exports.py:82,112`, `server/tests/test_simulation.py:129` | Corregir o justificar como `xfail`; suite 100% verde. | Confianza en el suite de tests. |
| **P-46** | `/data-sources` y `/sources` devuelven `url` interna al cliente | `server/src/routers/data.py:86-91` | No exponer `url` (clave de nube / ruta contenedor) en la respuesta al cliente; devolver solo metadatos seguros. | No se filtran rutas de almacenamiento ni claves de bucket. |
| **P-54** | Narrativa sin verificación numérica (fase general) | `server/src/engine/insight_auditor.py`, `analysis.py` | Extender verificación numérica a preguntas generales `/analyze` (no solo auditoría). | Cifras verificadas también en respuestas LLM normales. |

**Criterio de cierre Fase 3:** suite completa verde (`pytest` + `vitest`), `tsc` y `build` OK.

---

## Cómo proceder

1. Tú eliges con qué **fase** quieres comenzar (o apruebas todas).
2. Yo creo el `implementation_plan.md` detallado para la fase elegida.
3. Implemento de forma incremental: un problema a la vez, con tests y verificación (`tsc`, `vitest`, `pytest`, `build`).
4. Commiteo y pusheo solo lo aprobado.

**¿Con qué fase quieres empezar? ¿O prefieres que aborde un problema concreto primero?**

Responde con la fase (1, 2 o 3) o el ID del problema que quieras atacar primero, y yo preparo el plan detallado para tu aprobación antes de escribir código.
