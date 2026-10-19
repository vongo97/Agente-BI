# Registro de Problemas Conocidos — Vektra BI (Agente-BI)

> **Este documento es de lectura OBLIGATORIA antes de modificar cualquier archivo.**
> Regla asociada: `.codex/skills/known-issues-registry/SKILL.md`
> Última actualización: **2026-10-19** · Escaneo base: `bee43447`

---

## 1. Para qué existe

Evitar que los agentes (y las personas) **repitan los mismos errores**. Cada problema
registrado aquí incluye:

1. **Evidencia** (archivo:línea) para no discutir sobre suposiciones.
2. **Criterio de cierre** verificable (test o comando), para que "arreglado" no sea una opinión.
3. **Regla anti-repetición**, para que el patrón no vuelva a aparecer en otro archivo.

### Reglas del registro (no negociables)

| Regla | Detalle |
|---|---|
| **R1. IDs estables** | `P-XX` nunca se reutiliza ni se renumera. |
| **R2. No se borra** | Un problema se cierra (`CERRADO`), no se elimina. |
| **R3. Evidencia obligatoria** | Todo problema abierto cita `archivo:línea` o un comando reproducible. |
| **R4. Cierre con prueba** | `CERRADO` exige test, comando o captura que lo demuestre (se anota en la columna *Evidencia de cierre*). |
| **R5. Registrar antes de arreglar** | Si un agente descubre un problema nuevo, lo agrega aquí **antes** de corregirlo. |
| **R6. Mismo error dos veces = regla nueva** | Si un patrón reaparece, se crea una regla explícita y un test de regresión. |
| **R7. El estado manda** | `ABIERTO` no se puede ignorar si la tarea toca el área afectada. |
| **R8. Excepción de evolución** | Si un ajuste nuevo justificado choca con un comportamiento/test viejo, **manda el nuevo** y el viejo se actualiza en el mismo cambio. Se documenta qué contrato cambió. No sirve para revertir seguridad ni debilitar tests. |

### Estados

| Estado | Significado |
|---|---|
| `ABIERTO` | Confirmado y sin corregir. |
| `EN PROGRESO` | Hay una corrección en curso (anotar quién/cuándo). |
| `BLOQUEADO` | No se puede cerrar sin una decisión externa (credenciales, proveedor, etc.). |
| `CERRADO` | Corregido **y** verificado con evidencia. |
| `ACEPTADO` | Riesgo asumido conscientemente (requiere justificación escrita). |

### Severidad

| Nivel | Criterio |
|---|---|
| **CRÍTICO** | Compromete datos, credenciales, dinero o control de acceso. |
| **ALTO** | Rompe funcionalidad principal, seguridad relevante o despliegue. |
| **MEDIO** | Degrada calidad, mantenibilidad o experiencia de forma perceptible. |
| **BAJO** | Ruido, deuda menor o riesgo teórico. |

---

## 2. Resumen (ordenado de mayor a menor)

**Totales:** 3 críticos · 14 altos · 25 medios · 7 bajos · **49 problemas**

### 🔴 CRÍTICOS

| ID | Área | Problema | Estado | Evidencia |
|---|---|---|---|---|
| **P-01** | Auth | Bypass de autenticación *fail-open*: sin `ENVIRONMENT`/`RENDER` cualquier request entra como `test_user` y salta `AUTHORIZED_EMAILS` | ✅ CERRADO | `server/src/utils/common.py:98-163` · `tests/test_auth_bypass.py` |
| **P-02** | Datos | Sesiones guardadas con `pd.to_pickle` **en claro**, saltando el cifrado Fernet | ✅ CERRADO | `server/src/routers/data.py:378,517` · `tests/test_session_encryption.py` |
| **P-04** | Claves IA | Fallback a `gemini_key` aunque el proveedor activo sea otro → clave de Google enviada a terceros | ✅ CERRADO | `providers.py:394` · `dashboard.py`, `visual_summary.py`, `data.py`, `simulation.py` · `tests/test_key_resolution.py` |

### 🟠 ALTOS

| ID | Área | Problema | Estado | Evidencia |
|---|---|---|---|---|
| **P-03** | SQL | Modo SQL roto + controles `validate_sql_safety`/`execute_sql_safe` desconectados (código muerto) | ABIERTO | `analysis.py:119,137` · `bi_analyst.py:277-306` · `executor.py:377-383,874,913` |
| **P-05** | Frontend | Bucle infinito de `POST /dashboard/filter` (dependencia circular `items` → `setItems` → efecto) | ABIERTO | `client/src/components/DashboardView.tsx:177-194,242-248` |
| **P-06** | Dependencias | 11 vulnerabilidades npm (5 críticas): `next 16.1.1` (RCE/DoS), `next-auth beta.30` (fail-open), `plotly.js`→`maplibre-gl` | ABIERTO | `client/package.json` · `npm audit` |
| **P-07** | Frontend | CSP permisiva: `unsafe-inline`, `unsafe-eval`, `connect-src ws: wss:`, sin `frame-ancestors` | ABIERTO | `client/next.config.ts:19-28` |
| **P-08** | Frontend | Capa de red sin timeout, `AbortController`, retry ni reacción a 401/403 | ABIERTO | `client/src/lib/api.ts:15-32` |
| **P-09** | Frontend | Autosync guarda valores por defecto antes de cargar la config → puede sobrescribir ajustes del usuario | ABIERTO | `client/src/context/DashboardContext.tsx:138-211,216-246` |
| **P-10** | Cifrado | `ENCRYPTION_KEY` inválida genera clave efímera; `encrypt/decrypt` aceptan texto plano | ABIERTO | `server/src/utils/security.py:29-80` |
| **P-11** | Uploads | Original escrito en claro en `.tmp` antes de cifrar; sin mitigación de zip-bomb | ABIERTO | `server/src/routers/data.py:110-192` |
| **P-12** | API | `str(e)` de excepciones internas persistido y devuelto al cliente | ABIERTO | `server/src/routers/simulation.py:139,458,461` |
| **P-13** | UI/BI | KPIs inventados presentados como análisis real (`38.4 + n*1.2`, `96.5%`) | ABIERTO | `client/src/components/DashboardView.tsx:76-78` |
| **P-14** | UI/BI | El modelo mostrado en el selector no es el que usa el backend | ABIERTO | `ProviderKeysPanel.tsx:43-54,130` · `DashboardContext.tsx:146-167` |
| **P-15** | Auth | Sin allowlist ni middleware en el cliente: cualquier cuenta Google entra y la app queda inservible (403) | ABIERTO | `client/src/auth.ts:7-30` · `app/page.tsx:20-24` |
| **P-16** | Sandbox | Lista negra incompleta: `pd.read_table`, `DataFrame.to_csv`, `np.save`, `plt.savefig`, `pd.io.common.os`… | ABIERTO | `server/src/engine/executor.py:158-175,538-543,745-750` |
| **P-43** | API | `except Exception` de los endpoints de simulación se traga los `HTTPException` accionables → todo error se ve como 500 "Error interno" | ABIERTO | `simulation.py:158-168,672-692` · runtime `/simulation/generate-agents` |

### 🟡 MEDIOS

| ID | Área | Problema | Evidencia |
|---|---|---|---|
| **P-17** | Repo | Artefactos versionados: vídeo de **24 MB** y `debug_server.log` (361 KB) | `presentacion/2026-05-13 08-49-44.mp4`, `server/debug_server.log` |
| **P-18** | Código | `pkce_service.py` tiene **SyntaxError** (módulo no importable) | `server/src/services/pkce_service.py:90` |
| **P-19** | BD | `DATABASE_URL` inválida cae a SQLite en silencio; baseline de Alembic inválida | `server/src/database.py:35-48`, `server/main.py:128-130`, `migrations/versions/e114418c6081_*.py:24` |
| **P-20** | Legal | Páginas legales leen `../docs/legal` fuera de `client/` → 404 en Docker/standalone | `client/src/app/legal/[slug]/page.tsx:31-33` |
| **P-21** | Tests | Sin tests reales de JWT, `AUTHORIZED_EMAILS`, CORS, uploads maliciosos ni cifrado | `server/tests/test_auth.py`, `test_security_hardening.py:83` |
| **P-22** | API | `/health` sin auth y con sonda bloqueante a Supabase | `server/src/routers/health.py` |
| **P-23** | Deuda | Código muerto: `password_policy`, `mobile_security`, `reports.py`, visual-summary, `KpiCards`, `AnomalyAlert`, `ServerStatusTracker` | `server/src/...`, `client/src/...` |
| **P-24** | UI | Clases Tailwind inexistentes (`bg-bi-s0`, `text-bi-text-1`, `duration-3000`) | `SimAgentConfig.tsx:63-69`, `Skeletons.tsx:82` |
| **P-25** | A11y | Modal de reportes sin `role="dialog"`, ESC ni focus trap; toasts sin `aria-live` | `ReportBuilder.tsx:107-123`, `ToastContainer.tsx:40-41` |
| **P-26** | UI | "Guardar Cambios" en Ajustes no guarda nada y reporta éxito | `client/src/components/SettingsView.tsx:72-76` |
| **P-27** | UI | Fuentes guardadas se consultan pero nunca se renderizan (lista vacía al recargar) | `client/src/components/Sidebar.tsx:52-64,228-248` |
| **P-28** | Tests | Suite de cliente no ejecutable (`npm test` no existe) y expectativas desactualizadas | `client/package.json:5-10`, `client/src/tests/*` |
| **P-29** | UX | Sugerencias de chat sin cancelación + dataset inconsistente (última fuente vs primera) | `Chat.tsx:55-77,100`, `ChatSuggestions.tsx:50-53` |
| **P-30** | Rendimiento | Force layout O(n²) por frame sin parar; polling de simulación sin `try/catch` | `useForceLayout.ts:88-209`, `SimulationSandbox.tsx:139-154` |
| **P-31** | Infra | Rate limiting basado en IP de proxy (evadible con `X-Forwarded-For`) | `server/src/utils/limiter.py` |
| **P-32** | IA | Sin timeouts/reintentos en llamadas a LLM | `server/src/engine/providers.py:220` |
| **P-33** | Seguridad | `/connect-sql`: validación SSRF débil (DNS rebinding) y allowlist opcional | `security.py:108`, `data.py:313-326` |
| **P-34** | Datos | La sesión se guarda por usuario (sin `chat_id`) → conversaciones se pisan | `server/src/utils/common.py:188-197` |
| **P-35** | Memoria | `data_store` global en memoria sin límite ni TTL | `server/src/utils/common.py` |
| **P-44** | Frontend | Sin `GOOGLE_CLIENT_ID` la UI redirige a Google con `client_id=undefined` ("OAuth client was not found") en vez de avisar; sin fail-fast | `client/src/auth.ts`, `client/.env.local` · runtime navegador |
| **P-45** | Frontend | Error de hidratación en la landing (atributos SSR ≠ cliente) al cargar | `client/src/app/page.tsx` · consola del navegador |
| **P-47** | Dev/BD | `migrate_db.py` no cubre el drift real y revienta en Windows (`UnicodeEncodeError`); `create_all` no altera tablas → la app local da 500 por columnas faltantes | `server/src/utils/migrate_db.py:20-36` · runtime `/user-config` |
| **P-48** | API/BI | `/dashboard/filter` responde `200 success` con columnas inexistentes y no filtra en modo SQL (TODO) | `server/src/routers/dashboard.py:217-250` · runtime |
| **P-49** | Dev | No hay modo local sin nube: subir archivos exige Supabase válido (503 si no) y el arranque no lo avisa | `server/src/routers/data.py:212-241` · runtime `/upload` |

### 🟢 BAJOS

| ID | Área | Problema | Evidencia |
|---|---|---|---|
| **P-36** | Debug | `safe_error_message()` oculta el error real en logs; `except: pass` disperso | `logging_config.py`, `analysis.py:278` |
| **P-37** | Código | `generate_auto_dashboard` es un stub con TODO | `server/src/engine/...` |
| **P-38** | UI | Layout de dashboard desde `localStorage` sin validar; `any` en simulación | `DashboardView.tsx:222-229`, `useForceLayout.ts:13` |
| **P-39** | UI | Estado `pending` se etiqueta como "Fallo" | `SimHistory.tsx:42` |
| **P-40** | UI | Texto de 8-10 px y sidebar fija (`w-80`) en móvil | `SimHistory.tsx:12` y varios |
| **P-41** | Tests | 4 tests backend fallando (deuda de test, no regresión de producción) | `test_dashboard.py:97`, `test_exports.py:82`, `test_simulation.py:129` |
| **P-46** | API | `/data-sources` y `/sources` devuelven al cliente la `url` interna (clave de nube con el md5 del email o ruta del contenedor) | `server/src/routers/data.py:86-91` · runtime |

---

## 3. Fichas detalladas — CRÍTICOS (P-03 reclasificado a ALTO)

### P-01 · Bypass de autenticación *fail-open*

| Campo | Valor |
|---|---|
| **Severidad** | CRÍTICO |
| **Estado** | ✅ **CERRADO** (2026-10-19) |
| **Verificado** | ✅ Leyendo el código + 13 tests de regresión |
| **Archivos** | `server/src/utils/common.py:98-163`, `server/main.py:117-125`, `server/.env.example`, `server/tests/test_auth_bypass.py` |

**Qué pasaba.**
```python
is_dev = os.getenv("ENVIRONMENT", "development").lower() == "development"   # default inseguro
allow_bypass = (not is_render) and is_dev
if not auth_header: ... return "test_user_persistence@example.com"
```
Sin `ENVIRONMENT=production`, cualquier petición sin `Authorization` se autenticaba como
`test_user_persistence@example.com`, y `check_authorization()` lo eximía de `AUTHORIZED_EMAILS`.

**Impacto.** Control de acceso total sin credenciales en cualquier despliegue que olvidara dos
variables opcionales.

**Corrección aplicada.**
- `ENVIRONMENT` por defecto = **`production`** (fail-closed) y `is_development_mode()` como única fuente.
- Bypass exige **las tres** condiciones: `ENVIRONMENT` de desarrollo, `RENDER != true` y petición desde localhost.
- Sin contexto de request solo se permite en desarrollo (apps de test sin middleware); en producción siempre 401.
- Aviso explícito al arrancar si el modo desarrollo está activo.
- `ENVIRONMENT=development` documentado en `.env.example` y añadido al `.env` local para no cambiar el flujo de trabajo.

**Evidencia de cierre.**
```
tests/test_auth_bypass.py ............ 13 passed
suite completa ....................... 158 passed, 4 failed (P-41 preexistentes)

# Prueba end-to-end con la app real (TestClient):
ENVIRONMENT=production, sin token ......... 401  ✅
ENVIRONMENT=development + RENDER=true ..... 401  ✅
ENVIRONMENT=development + localhost ....... permitido (cubierto por test unitario)
```

**Regla anti-repetición.** Ningún control de seguridad puede activarse por *ausencia* de
configuración. Todo default desconocido = denegar.

---

### P-02 · Sesiones guardadas en claro con `pd.to_pickle`

| Campo | Valor |
|---|---|
| **Severidad** | CRÍTICO |
| **Estado** | ✅ **CERRADO** (2026-10-19) |
| **Verificado** | ✅ Leyendo el código + 5 tests de regresión |
| **Archivos** | `server/src/routers/data.py:378,517` · `server/tests/test_session_encryption.py` |

**Qué pasaba.** `pd.to_pickle(session_data, get_session_file(user))` escribía el pickle sin pasar por
`save_user_data()`/`encrypt_file()`. El resto del sistema cifra con Fernet; estas dos rutas no.

**Impacto.** Datos del usuario (posible PII) en claro en disco/backups. Además `pickle` es RCE si
el archivo es manipulable.

**Corrección aplicada.**
- Los dos flujos (`Google Sheets` y `limpieza con IA`) usan ahora `save_user_data()`, que serializa,
  **cifra con Fernet** y sincroniza a la nube.
- Se mantiene el cache en memoria (`data_store`) actualizado en ambos puntos, igual que antes.

**Evidencia de cierre.**
```
tests/test_session_encryption.py ..... 5 passed
  - archivo empieza por token Fernet (gAAA...)
  - no hay nombres de columnas ni metadata en claro
  - roundtrip: save -> clear cache -> get_user_data recupera el DataFrame
  - guardia estática: data.py no contiene pd.to_pickle
  - guardia estática: 2 usos de save_user_data

suite completa ...................... 163 passed, 4 failed (P-41 preexistentes)
```

**Regla anti-repetición.** Toda persistencia pasa por **una sola** función (`save_user_data`).
Prohibido `to_pickle`, `to_csv`, `open(...,"w")` directo en routers.

---

### P-03 · Modo SQL roto y controles SQL desconectados *(reclasificado de CRÍTICO a ALTO)*

| Campo | Valor |
|---|---|
| **Severidad** | ALTO (reclasificado tras verificación profunda) |
| **Estado** | ABIERTO |
| **Verificado** | ✅ Lectura completa del flujo (no solo `grep`) |
| **Archivos** | `server/src/routers/analysis.py:119,137` · `server/src/engine/bi_analyst.py:277-306` · `server/src/engine/executor.py:377-383,874,913` |

**Qué pasa realmente (corrección del hallazgo inicial).**
La primera auditoría afirmó que el `engine` SQLAlchemy se inyectaba en el sandbox. **No es así**:
`analysis.py:119` calcula `data_var = ... else "engine"`, pero **esa variable nunca se usa**. El flujo real es:

1. `/connect-sql` guarda `{"type": "sql", "data": engine}` (`data.py:331`).
2. `/analyze` pasa ese `engine` a `analyze_data()` (`analysis.py:137`).
3. `analyze_data()` solo entiende `dict` de DataFrames o un `DataFrame`; con un `engine` cae en
   `data_context.columns` (`bi_analyst.py:300`) → excepción.
4. Aunque llegara al sandbox, `execute_analysis()` solo serializa `DataFrame`/`dict` (`executor.py:377-383`),
   así que el `engine` **no es alcanzable** desde el código del LLM.

Conclusión: **el modo SQL no funciona** y `validate_sql_safety()`/`execute_sql_safe()` (whitelist de
solo lectura) **no se llaman desde ningún flujo**: son código muerto.

**Impacto.**
- Funcional: un usuario que conecta una base SQL y pregunta en el chat obtiene error (la feature está rota).
- Seguridad: existe una barrera SQL escrita y probada… pero desconectada. El día que alguien "active"
  el modo SQL sin cablearla, se ejecutaría SQL sin validar.
- No hay RCE ni escritura en la BD por esta vía en el estado actual (el `engine` no entra al subproceso).

**Criterio de cierre.**
- El modo SQL materializa datos con `execute_sql_safe()` (que valida con `validate_sql_safety`) y el
  análisis trabaja sobre DataFrames normales.
- Tests: `SELECT` permitido; `DROP`, `DELETE`, `UPDATE`, `INSERT`, `;` múltiple, `pg_read_file` → rechazados.
- Guardia estática: `validate_sql_safety` debe estar referenciada desde el flujo de análisis.

**Regla anti-repetición.** Una función de seguridad que no está cableada al flujo **no existe**.
Todo control debe tener un test que falle si se desconecta.

---

### P-04 · Clave de Gemini enviada a otros proveedores

| Campo | Valor |
|---|---|
| **Severidad** | CRÍTICO |
| **Estado** | ✅ **CERRADO** (2026-10-19) |
| **Verificado** | ✅ Lectura del flujo real + 14 tests de regresión |
| **Archivos** | `dashboard.py` · `visual_summary.py` · `data.py` · `simulation.py` · `providers.py` · `tests/test_key_resolution.py` |

**Qué pasaba.** Patrón repetido en 6 sitios:
```python
elif (len(api_key) < 10 or "..." in api_key) and user_config.gemini_key:
    api_key = decrypt_key(user_config.gemini_key)
```
No miraba qué proveedor estaba activo: con OpenAI/Anthropic/DeepSeek/OpenRouter/NVIDIA
seleccionado y la clave enmascarada o vacía, se enviaba **la clave de Google** a ese otro vendor.

**Impacto.** Fuga de credencial a un tercero + cargos cruzados + fallo de autenticación.
`resolve_keys()` en `providers.py` ya lo hacía bien, pero estos flujos lo puenteaban.

**Corrección aplicada.**
- `resolve_keys()` ahora resuelve `hybrid` como Gemini + Mistral (antes `hybrid` no leía la
  clave de Gemini de la BD) y resuelve Mistral también en `hybrid`.
- `dashboard.py`, `visual_summary.py`, `data.py`, `simulation.py` (`create_simulation` y
  `generate-agents`) usan `resolve_keys(<proveedor activo>, ...)` y propagan el error.
- En `simulation.py`, la clave de Gemini se usa **solo** para el cliente de Gemini del
  enjambre (`gemini_key = key if prov == "gemini" else ...`), nunca como clave de otro proveedor.

**Revisado y descartado (no hay cruce de claves).**
- `exports.py:158` → `create_presentation()` llama a Gemini con `provider="gemini"` fijo
  (`pptx_generator.py:86,128`): la clave de Gemini sí corresponde.
- `simulation.py` suggestions/ontology → usan la clave de Gemini **contra la API de Gemini**
  (incluido el fallback documentado tras un fallo de Groq). No hay fuga; el defecto real
  (ignorar el proveedor elegido) queda registrado como **P-42**.

**Evidencia de cierre.**
```
tests/test_key_resolution.py .............. 14 passed (9 subtests)
  - openai/anthropic/deepseek/openrouter/nvidia nunca reciben gemini_key
  - mistral viaja en su propio campo; hybrid usa Gemini + Mistral
  - clave enviada por el cliente manda si es utilizable
  - sin clave propia -> error explícito, nunca la de Gemini
  - guardias estáticas: sin `user_config.gemini_key` y con `resolve_keys(provider, ...)`
  - guardias estáticas en simulation.py (create_simulation y generate-agents)

suite completa ............................ 177 passed, 4 failed (P-41 preexistentes)
```

**Regla anti-repetición.** Una sola función resuelve credenciales (`resolve_keys`).
Prohibido `user_config.<proveedor>_key` o `config.gemini_key` fuera de `providers.py`
salvo para construir un cliente de **ese mismo** proveedor.

---

## 4. Fichas detalladas — ALTOS

### P-05 · Bucle infinito de filtros del dashboard
**Archivos:** `client/src/components/DashboardView.tsx:177-194`, `:242-248`.

`applyRemoteFilters` es `useCallback` con `items` en las dependencias y hace `setItems(updatedItems)`
con un array nuevo. El efecto depende de `applyRemoteFilters` → cada respuesta cambia la identidad
del callback → vuelve a disparar la petición. Con cualquier filtro activo **no converge**:
lluvia de `POST /dashboard/filter`, 429, dashboard inutilizable.

**Cierre:** el efecto no depende de `items`; la actualización es funcional (`setItems(prev => ...)`)
y se compara por `id`. Test: con filtro activo, un solo POST por cambio de filtro.

**Regla:** nunca pongas en las dependencias de un efecto un valor que ese mismo efecto modifica.

---

### P-06 · Dependencias vulnerables
**Archivo:** `client/package.json`. `npm audit`: **11 vulnerabilidades (5 críticas, 3 altas)**.
- `next 16.1.1` → **fix `16.4.2`** (no es cambio de major). Incluye RCE no autenticado en servidores Windows.
- `next-auth 5.0.0-beta.30` → *sin fix publicado*: "configuration errors fail open".
- `plotly.js` → `maplibre-gl` XSS (sin fix en el rango).
- `vitest`/`tinypool` → RCE por prototype pollution (dev).

**Cierre:** `next@16.4.2`, `npm audit` sin críticas de runtime; build verde. `next-auth` documentado como riesgo aceptado hasta release.

**Regla:** ningún deploy sin `npm audit` revisado; las críticas de runtime bloquean el release.

---

### P-07 · CSP permisiva
**Archivo:** `client/next.config.ts:19-28`.
`script-src 'self' 'unsafe-eval' 'unsafe-inline'`, `connect-src ws: wss:` (cualquier host),
sin `frame-ancestors`, `base-uri` ni `form-action`. Cualquier script inline inyectado se ejecuta.

**Cierre:** nonce/hash para el bootstrap de tema, `connect-src` explícito (API + Supabase),
`frame-ancestors 'none'`, `base-uri 'self'`, `form-action 'self'`. Verificar en DevTools sin errores.

**Regla:** `unsafe-inline` en `script-src` solo se acepta con justificación escrita y fecha de retirada.

---

### P-08 · Capa de red sin timeout ni reacción a 401/403
**Archivo:** `client/src/lib/api.ts:15-32` (~30 llamadas).
Sin `AbortController`, sin timeout, sin retry/backoff. Un LLM lento cuelga la UI indefinidamente;
un token caducado produce fallos silenciosos repetidos.

**Cierre:** timeout configurable (p. ej. 120 s, mayor en análisis), cancelación al desmontar,
401 → re-login, 403 → mensaje claro + sign-out. Tests del wrapper.

**Regla:** toda llamada de red del cliente pasa por `securedFetch`; prohibido `fetch` directo.

---

### P-09 · El autosync puede sobrescribir la configuración guardada
**Archivo:** `client/src/context/DashboardContext.tsx:138-211`, `:216-246`.
13+ efectos llaman `syncConfig` con **valores por defecto** en el primer render, antes de que
`getUserConfig` resuelva. Con el debounce de 1.2 s, la respuesta lenta llega después y los
defaults ya están en cola → se persisten y pisan lo del servidor.

**Cierre:** `syncConfig` no se ejecuta hasta `configLoaded === true`; el debounce se limpia al
desmontar; test de carga lenta que verifica que no se envía config antes de hidratar.

**Regla:** nunca sincronices estado antes de hidratarlo desde la fuente de verdad.

---

### P-10 · Cifrado degradado silenciosamente
**Archivo:** `server/src/utils/security.py:29-80`.
`ENCRYPTION_KEY` ausente/inválida → clave efímera en memoria; `encrypt_key`/`decrypt_key`
aceptan y devuelven texto plano. Al reiniciar, lo cifrado con la clave efímera es ilegible.

**Cierre:** sin `ENCRYPTION_KEY` válida el arranque **falla** con mensaje claro; no hay rama de
texto plano; test de arranque sin clave → excepción.

**Regla:** un fallback de seguridad que "funciona" es peor que un fallo ruidoso.

---

### P-11 · Upload: `.tmp` en claro y zip-bomb
**Archivo:** `server/src/routers/data.py:110-192`.
Se escribe el original a `permanent_path + ".tmp"` sin cifrar antes de `encrypt_file`; los límites
(25 MB / 1M celdas) se comprueban **después** de abrir el Excel/zip; sin ratio de compresión.

**Cierre:** cifrado en streaming (sin `.tmp` en claro) y límites de expansión antes de parsear;
test con zip-bomb y con archivo que excede cuota.

**Regla:** nunca escribas datos de usuario en claro, ni siquiera "un momento".

---

### P-12 · Errores internos devueltos al cliente
**Archivo:** `server/src/routers/simulation.py:139`, `:458`, `:461`.
`f"Error: {type(e).__name__} - {str(e)}"` se persiste y se devuelve en el JSON.

**Verificado en runtime (2026-10-19):** `GET /api/v1/user-config` → `500`
`{"detail":"Internal Server Error: OperationalError"}`, exponiendo la clase de excepción y el
motor de base de datos al cliente.

**Cierre:** mensaje genérico al cliente + `X-Request-Id`; detalle solo en logs internos.

**Regla:** el cliente recibe código y request-id, nunca el texto de la excepción.

---

### P-13 · KPIs fabricados
**Archivo:** `client/src/components/DashboardView.tsx:76-78`.
"Saturación Global" = `38.4 + items.length * 1.2`; "Confianza del Análisis" = `96.5%` fijo.
Se presentan como resultados de negocio.

**Cierre:** métricas calculadas con datos reales o retiradas/etiquetadas como demostración.

**Regla:** ningún número mostrado al usuario puede ser inventado. Si no hay dato, se dice.

---

### P-14 · El selector de modelo miente
**Archivos:** `ProviderKeysPanel.tsx:43-54,130` · `DashboardContext.tsx:146-167`.
`provider_models` se guarda pero nunca se lee; `ensureModels` pone `models[0]` al enfocar.

**Cierre:** al cargar, el selector muestra el modelo persistido; test de recarga.

**Regla:** la UI nunca debe inferir el estado del servidor: lo lee.

---

### P-15 · Sin allowlist en el cliente
**Archivos:** `client/src/auth.ts:7-30`, `client/src/app/page.tsx:20-24`.
Cualquier cuenta Google completa el OAuth y entra a la UI; todas las llamadas dan 403.

**Cierre:** callback `signIn` valida la lista autorizada (o middleware), mensaje claro y sign-out.

**Regla:** la autorización se valida en el servidor **y** se refleja en el cliente para no dejar al usuario en un callejón sin salida.

---

### P-16 · Lista negra del sandbox incompleta
**Archivo:** `server/src/engine/executor.py:158-175`, `:538-543`, `:745-750`.
Se bloquean strings exactos (`read_csv`, `open`, `os`…) pero no `pd.read_table`,
`DataFrame.to_csv`, `np.save`, `plt.savefig`, `pd.io.common.os`, `pd.io.common.urlopen`,
`getattr`/alias.

**Cierre:** allowlist (no lista negra) de módulos/atributos + bloqueo de `getattr` dinámico;
tests para cada bypass conocido.

**Regla:** en seguridad, listas negras = falsa sensación de protección. Usa allowlist.

---

### P-43 · Los endpoints de simulación se tragan los errores accionables

| Campo | Valor |
|---|---|
| **Severidad** | ALTO |
| **Estado** | ABIERTO (hallado en la prueba local del 2026-10-19) |
| **Verificado** | ✅ Runtime: `POST /simulation/generate-agents` → 500 |
| **Archivos** | `server/src/routers/simulation.py` (`create_simulation` y `generate_agents_endpoint`) |

**Qué pasa.** El cuerpo entero del endpoint va dentro de `try: ... except Exception as e:` y ese
`except` convierte **cualquier** excepción en `HTTPException(500, "Error interno…")`. Como
`HTTPException` hereda de `Exception`, las negativas deliberadas (400 "no hay clave de OpenAI
guardada", 401, 404) **también se convierten en 500** y pierden su mensaje. El log solo guarda
`type(e).__name__`, así que el motivo tampoco queda registrado.

**Evidencia de runtime (local).**
```
POST /api/v1/simulation/generate-agents  {"provider":"openai","apiKey":"","selectedIds":[17]}
  -> 500 {"detail":"Error interno al generar agentes del debate."}
POST /api/v1/analyze  (mismo caso)      -> 400 {"detail":"No hay ninguna clave de OpenAI guardada…"}
log: [Sim-agents] Error al generar agentes: OperationalError   (nunca el motivo real)
```
Durante la prueba, un problema de esquema de la BD local (`no such column`) también apareció como
"Error interno", imposible de diagnosticar desde la UI.

**Impacto.** El usuario no sabe qué corregir (clave, archivo, cuota) y soporte no tiene traza.
Los endpoints afectados son justo los que dependen de claves del usuario.

**Cierre.** Re-lanzar `HTTPException` antes del `except` genérico (`except HTTPException: raise`) en
todos los endpoints afectados; loguear el mensaje saneado, no solo el tipo. Test: provider sin clave
→ 400 con el texto del proveedor; fallo inesperado → 500.

**Regla anti-repetición.** Un `except Exception` nunca debe envolver las validaciones ni las
respuestas HTTP deliberadas. Primero `except HTTPException: raise`.

---

## 5. Fichas resumidas — MEDIOS y BAJOS

**P-17** · Repo inflado. Sacar el `.mp4` (24 MB) y `debug_server.log` del índice; `.gitignore`. *Cierre:* `git ls-files` sin binarios ni logs.
**P-18** · `pkce_service.py:90` SyntaxError. *Cierre:* `python -c "ast.parse(...)"` OK o archivo eliminado por código muerto.
**P-19** · Fallback silencioso a SQLite + baseline Alembic inválida. *Verificado en runtime (2026-10-19):* la SQLite local quedó desfasada respecto a los modelos (`no such column: user_configs.code_verifier`) → `GET /user-config` 500 y `resolve_keys()` reventando en los endpoints de simulación; `create_all()` no altera tablas y `migrate_db.py` no cubre ese drift (ver P-47). *Cierre:* `DATABASE_URL` inválida aborta el arranque; `alembic upgrade head` funciona en limpio.
**P-20** · Páginas legales leen fuera de `client/`. *Cierre:* los `.md` viven dentro de `client/` o se empaquetan; build standalone las sirve.
**P-21** · Tests sin JWT/CORS/uploads/cifrado reales. *Cierre:* tests que fallen si se desactiva cada control.
**P-22** · `/health` público y bloqueante. *Cierre:* sonda con timeout y sin datos sensibles; opcional proteger detalle.
**P-23** · Código muerto (~1.500 líneas frontend + módulos backend). *Cierre:* eliminar o registrar como `ACEPTADO`.
**P-24** · Tokens Tailwind inexistentes. *Cierre:* usar `--color-bi-*` reales; revisión visual del paso de configuración.
**P-25** · A11y modal/toasts. *Cierre:* `role="dialog"`, `aria-modal`, ESC, focus trap, `aria-live`.
**P-26** · "Guardar Cambios" no-op. *Cierre:* botón ejecuta el guardado real o se elimina.
**P-27** · Fuentes guardadas no renderizadas. *Cierre:* la lista se pinta desde la API al cargar.
**P-28** · Tests frontend no ejecutables. *Cierre:* `npm test` verde en CI.
**P-29** · Sugerencias de chat en bucle/dataset inconsistente. *Cierre:* efecto sin `suggestions.length`; misma fuente que el análisis; cancelación.
**P-30** · Force layout O(n²) + polling sin guard. *Cierre:* `requestAnimationFrame` se detiene al estabilizar; interval con `try/catch` y deps estables.
**P-31** · Rate limit por IP de proxy. *Cierre:* `X-Forwarded-For` confiable/`ProxyHeadersMiddleware`; test de bypass.
**P-32** · Sin timeouts LLM. *Cierre:* timeout+retry con backoff; error controlado al usuario.
**P-33** · SSRF en `/connect-sql`. *Cierre:* allowlist obligatoria en producción + bloqueo de IPs privadas tras resolver.
**P-34** · Sesión sin `chat_id`. *Cierre:* archivo por `user+chat`; test de dos conversaciones simultáneas.
**P-35** · `data_store` sin límite. *Cierre:* LRU/TTL o persistencia; test de crecimiento.
**P-36** · Errores ocultos (`safe_error_message`, `except: pass`). *Cierre:* log con tipo+mensaje saneado y `request_id`; prohibido `except: pass`.
**P-37** · `generate_auto_dashboard` stub. *Cierre:* implementar o devolver 501 explícito.
**P-38** · `localStorage` sin validar y `any`. *Cierre:* validación de esquema y tipos reales.
**P-39** · `pending` = "Fallo". *Cierre:* mapear estados correctamente.
**P-40** · Tipografía 8-10 px y sidebar fija. *Cierre:* mínimo 12 px y responsive.
**P-41** · 4 tests backend fallando. *Cierre:* suite 100% verde (o `xfail` justificado).
**P-42** · Proveedor ignorado en simulación: `/simulation/suggestions` y `/simulation/ontology` usan siempre Gemini (`simulation.py:339,402` y `:563`) aunque el usuario elija otro proveedor → resultados de otro modelo, sin aviso. **No hay fuga de claves** (la clave de Gemini va contra la API de Gemini). *Verificado en runtime (2026-10-19):* `POST /simulation/suggestions` con `provider=openai` responde `"API key must be set when using the Google AI API"` (demostró que ejecutó Gemini) y `/simulation/ontology` devuelve `{"nodes":[],"edges":[]}` con HTTP 200 (fallo silencioso). *Cierre:* ambos endpoints resuelven el proveedor con `resolve_keys()` y despachan al vendor elegido (o rechazan explícitamente los no soportados); test que falle si vuelven a caer en Gemini. **Regla:** lo que el selector promete es lo que se ejecuta.

---

## 6. Cómo agregar un problema nuevo

1. Asignar el siguiente ID libre (`P-42`, `P-43`…). **Nunca reutilizar.**
2. Completar: severidad, área, evidencia (`archivo:línea` o comando), impacto, criterio de cierre y regla anti-repetición.
3. Añadirlo a la tabla de su severidad y actualizar el contador del resumen.
4. Si el patrón ya existía, **no crear otro ID**: ampliar el existente y añadir la regla.

## 7. Historial

| Fecha | Cambio |
|---|---|
| 2026-10-19 | Creación del registro con 41 problemas del escaneo completo (`bee43447`). |
| 2026-10-19 | **P-01 CERRADO**. Contrato cambiado: `ENVIRONMENT` ahora es `production` por defecto y el bypass de token exige desarrollo + localhost + no-Render. Ajustados en el mismo cambio: `common.py`, `main.py`, `.env.example`, `.env` local y 13 tests nuevos. |
| 2026-10-19 | **P-02 CERRADO**. Los dos `pd.to_pickle` de `data.py` pasan a `save_user_data()` (Fernet + nube). 5 tests nuevos, incluida guardia estática contra reintroducir escritura en claro. |
| 2026-10-19 | **P-03 reclasificado CRÍTICO → ALTO** tras verificación profunda: el `engine` nunca entra al subproceso (el sandbox solo serializa DataFrames), por lo que no hay RCE; el problema real es que el **modo SQL está roto** y la validación read-only está desconectada. |
| 2026-10-19 | **P-04 CERRADO**. `dashboard.py`, `visual_summary.py`, `data.py` y `simulation.py` (crear simulación y generar agentes) resuelven la clave con `resolve_keys()`; la clave ya no cruza de proveedor. 14 tests nuevos. Registrado **P-42** (endpoints de simulación que ignoran el proveedor elegido; sin fuga de claves). |
| 2026-10-19 | **Prueba local (modo simulación) con backend + frontend reales.** Confirmados: bypass de desarrollo (P-01), cifrado Fernet de archivos y sesiones (P-02), rechazo SSRF de `/connect-sql` (P-33), validaciones de subida (extensión y path traversal), `resolve_keys` devolviendo el mensaje del **proveedor correcto** en `/analyze` y `/visual-summary` (P-04). Nuevos hallazgos registrados: **P-43** (ALTO), **P-44**, **P-45**, **P-47**, **P-48**, **P-49** (MEDIOS) y **P-46** (BAJO); P-42 confirmado en runtime. Detalle en la sección 8. |

---

## 8. Pruebas locales (modo simulación)

Cómo se levanta el entorno y **qué se comprobó de verdad** (2026-10-19). Sirve para repetir la
verificación sin tener que redescubrirla.

### Arranque
```powershell
# backend (usa el venv del proyecto y el .env local con ENVIRONMENT=development)
cd server; .\.venv-codex\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
# frontend (npm falla en PowerShell; usar cmd)
cd client; cmd /c "npm run dev"      # http://localhost:3000
```
Sin `SUPABASE_*` válidas no se puede subir por `/upload` (fail-closed, ver P-49). Para probar el
resto de flujos con datos, la alternativa usada fue **sembrar la fuente de forma cifrada** (script
de simulación: copia el CSV → `encrypt_file` → fila `DataSource` → `save_user_data`). Limpieza:
borrar la fila y los archivos generados.

### Qué funciona (verificado en runtime)
| Prueba | Resultado |
|---|---|
| `GET /health` | 200 · sqlite · nube `connected:false` |
| Petición sin token desde localhost (dev) | 200 como `test_user` (P-01 ✅) |
| Petición sin token con `RENDER=true` | 401 (verificado en el arreglo de P-01) |
| `GET /api/v1/providers` | 200 · catálogo sin secretos |
| `POST /upload` con `.txt` | 400 "Extensión no permitida" |
| `POST /upload` con nombre `../evil.csv` | 400 "Nombre de archivo inválido" |
| `POST /connect-sql` a `localhost` | 400 "No se permiten conexiones a hosts locales" (P-33 ✅) |
| `POST /analyze` `provider=openai` sin clave | 400 con el texto de **OpenAI** (P-04 ✅) |
| `POST /visual-summary` `provider=openai` sin clave | 400 con el texto de **OpenAI** (P-04 ✅) |
| Archivo y sesión en disco | empiezan por `gAAA` (Fernet) y no hay datos en claro (P-02 ✅) |
| Frontend dev server | compila y sirve la landing + `/login` |

### Qué está mal (hallazgos registrados)
| Prueba | Resultado | Problema |
|---|---|---|
| `GET /api/v1/user-config` | 500 `Internal Server Error: OperationalError` (drift de SQLite) | P-19, P-47, P-12 |
| `POST /simulation/generate-agents` sin clave | 500 "Error interno" (el 400 accionable se pierde) | P-43 |
| `POST /simulation/suggestions` `provider=openai` | responde con error de **Google AI API** (usó Gemini) | P-42 |
| `POST /simulation/ontology` `provider=openai` | `{"nodes":[],"edges":[]}` 200 (fallo silencioso) | P-42 |
| `POST /dashboard/filter` `{"NoExiste":123}` | 200 `success` sin filtrar | P-48 |
| `GET /api/v1/data-sources` | devuelve `url` interna al cliente | P-46 |
| `POST /upload` con CSV válido | 503 (nube no disponible) | P-49 |
| Landing en el navegador | error de hidratación en consola | P-45 |
| "Continuar con Google" sin `GOOGLE_CLIENT_ID` | Google: `client_id=undefined` → "OAuth client was not found" | P-44 |

### Acciones de entorno pendientes (no son código)
1. **`SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` del `.env` local no funcionan** (`SupabaseException`
   al crear el cliente). Mientras no se renueven, no hay subidas ni persistencia en nube en local.
2. **`GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`** no están en `client/.env.local` → la UI local no
   se puede usar más allá del login.
3. `ENCRYPTION_KEY`, `AUTH_SECRET` y `DATABASE_URL`: presentes y operativos en el `.env` local.
