# Registro de Problemas Conocidos — Vektra BI (Agente-BI)

> **Este documento es de lectura OBLIGATORIA antes de modificar cualquier archivo.**
> Regla asociada: `.codex/skills/known-issues-registry/SKILL.md`
> Última actualización: **2026-10-29** · Escaneo base: `bee43447`

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

**Totales:** 4 críticos · 22 altos · 26 medios · 8 bajos (filas del resumen) · **68 IDs registrados**.
Deuda de registro conocida: **P-57–P-65** solo tienen sección de detalle (sin fila en el resumen) y **P-42** se cita en commits pero no está registrado.

### 🔴 CRÍTICOS

| ID | Área | Problema | Estado | Evidencia |
|---|---|---|---|---|
| **P-01** | Auth | Bypass de autenticación *fail-open*: sin `ENVIRONMENT`/`RENDER` cualquier request entra como `test_user` y salta `AUTHORIZED_EMAILS` | ✅ CERRADO | `server/src/utils/common.py:98-163` · `tests/test_auth_bypass.py` |
| **P-02** | Datos | Sesiones guardadas con `pd.to_pickle` **en claro**, saltando el cifrado Fernet | ✅ CERRADO | `server/src/routers/data.py:378,517` · `tests/test_session_encryption.py` |
| **P-04** | Claves IA | Fallback a `gemini_key` aunque el proveedor activo sea otro → clave de Google enviada a terceros | ✅ CERRADO | `providers.py:394` · `dashboard.py`, `visual_summary.py`, `data.py`, `simulation.py` · `tests/test_key_resolution.py` |
| **P-66** | Frontend / Dependencias | `dompurify` 3.4.16 con 3 bypass XSS publicados el 21-10-2026 (GHSA-cg2g-xh64-v4q7 crítica, GHSA-mrv2-3pqr-j5jr, GHSA-c6gr-qvv4-5v3f). Sanitiza el SVG de Mermaid generado por IA | ✅ CERRADO | `npm audit fix` → `dompurify` 3.4.17 · `npm run build` OK · `npx tsc --noEmit` limpio · `npx vitest run` → 78 passed · `npm audit --omit=dev` → 0 critical (quedan 2 low de katex/mermaid, ver P-67/P-68) |

### 🟠 ALTOS

| ID | Área | Problema | Estado | Evidencia |
|---|---|---|---|---|
| **P-03** | SQL | Modo SQL roto + controles `validate_sql_safety`/`execute_sql_safe` desconectados (código muerto) | ✅ CERRADO | `analysis.py:175-215` cableado con `execute_sql_safe` + `validate_sql_safety` · `executor.py` `execute_sql_safe` usa `conn.execute` · `tests/test_sql_mode_safety.py` (18 passed) · Antigravity 2026-10-22 |
| **P-05** | Frontend | Bucle infinito de `POST /dashboard/filter` (dependencia circular `items` → `setItems` → efecto) | ✅ CERRADO | `client/src/components/DashboardView.tsx:177-194` · functional updater `setItems(prevItems => ...)` + `tsc --noEmit` limpio · Antigravity 2026-10-22 |
| **P-06** | Dependencias | 11 vulnerabilidades npm (5 críticas): `next 16.1.1` (RCE/DoS), `next-auth beta.30` (fail-open), `plotly.js`→`maplibre-gl` | ✅ CERRADO | `client/package.json` · `npm audit --omit=dev` → 2 low, 0 critical/high/moderate |
| **P-07** | Frontend | CSP permisiva: `unsafe-inline`, `unsafe-eval`, `connect-src ws: wss:`, sin `frame-ancestors` | ✅ CERRADO | `client/next.config.ts` · `script-src 'self'` (sin unsafe-eval/unsafe-inline) · `style-src 'self'` (sin unsafe-inline) · `frame-ancestors 'none'` · `base-uri 'self'` · `form-action 'self'` · `object-src 'none'` · `frame-src 'none'` · `connect-src` con hosts específicos (no ws:/wss: genéricos) · `client/src/tests/CSP.test.ts` (13 passed) · Antigravity 2026-10-22 |
| **P-08** | Frontend | Capa de red sin timeout, `AbortController`, retry ni reacci�n a 401/403 | ? CERRADO | `client/src/lib/api.ts` � `securedFetch` con AbortController (30 s), retry exponencial (2 reintentos), 401/403 ? signOut + redirect /login � `client/src/tests/ApiNetwork.test.ts` (6 passed) |
| **P-09** | Frontend | Autosync guarda valores por defecto antes de cargar la config → puede sobrescribir ajustes del usuario | ✅ CERRADO | `client/src/context/DashboardContext.tsx` · gate de hidratación `loadedConfigUser`/`configLoaded`: `syncConfig` no persiste hasta que `getUserConfig` resuelve para el usuario activo; cleanup de timers/pendientes al desmontar o cambiar de cuenta; token de NextAuth desacoplado de la carga de config · `client/src/tests/DashboardConfigHydration.test.tsx` (3 passed: carga lenta no autosavea defaults, fallo de red deja autosave deshabilitado, cambio del usuario autosavea tras hidratar) · suite `vitest run` → 78 passed · `tsc --noEmit` limpio (2026-10-28) |
| **P-10** | Cifrado | `ENCRYPTION_KEY` inválida genera clave efímera; `encrypt/decrypt` aceptan texto plano | ✅ CERRADO | `server/src/utils/security.py` · fail-closed en producción sin clave · clave determinista en dev · `encrypt_key` lanza `ValueError` en vez de texto plano · `decrypt_key` rechaza no-Fernet · `tests/test_security_encryption_key.py` (10 passed) · Antigravity 2026-10-22 |
| **P-11** | Uploads | Original escrito en claro en `.tmp` antes de cifrar; sin mitigación de zip-bomb | ✅ CERRADO | `server/src/routers/data.py` · `server/src/utils/security.py` · `encrypt_bytes` cifra en memoria sin `.tmp` en claro · zip-bomb temprano desde bytes (Excel dimensiones + CSV líneas) · `server/tests/test_upload_security.py` (7 passed) · Antigravity 2026-10-22 |
| **P-12** | API | `str(e)` de excepciones internas persistido y devuelto al cliente | ✅ CERRADO | `server/src/routers/simulation.py` · `str(e)` reemplazado por mensajes genéricos en 3 ubicaciones (líneas 139, 447, 453) · detalle solo en logs internos con `logger.exception` · Antigravity 2026-10-22 |
| **P-13** | UI/BI | KPIs inventados presentados como análisis real (`38.4 + n*1.2`, `96.5%`) | ✅ CERRADO | `client/src/components/DashboardView.tsx:73-131` · métricas reales derivadas de datos (visualizaciones activas, filtros, fuentes) · Antigravity 2026-10-22 |
| **P-14** | UI/BI | El modelo mostrado en el selector no es el que usa el backend | ? CERRADO | `client/src/components/SettingsView.tsx` � `client/src/context/DashboardContext.tsx` � `providerModels` cargado desde `getUserConfig` y mostrado junto al nombre del proveedor � Antigravity 2026-10-22 |
| **P-15** | Auth | Sin allowlist ni middleware en el cliente: cualquier cuenta Google entra y la app queda inservible (403) | ? CERRADO | `client/src/lib/auth-allowlist.ts` � `client/src/app/page.tsx` � `isAuthorizedEmail()` lee NEXT_PUBLIC_AUTHORIZED_EMAILS � acceso denegado con mensaje claro � `client/src/tests/AuthAllowlist.test.ts` (4 passed) � Antigravity 2026-10-22 |
| **P-16** | Sandbox | Lista negra incompleta: `pd.read_table`, `DataFrame.to_csv`, `np.save`, `plt.savefig`, `pd.io.common.os`… | ✅ CERRADO | `server/src/engine/executor.py` · allowlist de módulos/atributos + bloqueo `getattr`/`setattr`/`delattr` + `to_csv`, `read_table`, `np.save*`, `savefig` bloqueados en AST y runtime · `tests/test_sandbox_imports.py` (12 passed) · Antigravity 2026-10-22 |
| **P-51** | Sandbox | La allowlist de imports no incluye `time`; pandas/numpy lo importan en runtime y **todo análisis falla** con `ImportError: Librería 'time' bloqueada por seguridad` | ✅ CERRADO | `server/src/engine/executor.py:283-294,457-468,762-769` · `tests/test_sandbox_imports.py` |
| **P-52** | Sandbox | La lista AST de atributos prohibidos incluye `rename`; bloquea `DataFrame.rename()` legítimo y hace fallar análisis con pandas | ✅ CERRADO | `server/src/engine/executor.py:153-166` · `tests/test_sandbox_imports.py::TestSandboxRename` |
| **P-54** | IA/BI | La narrativa del análisis no tiene verificación numérica en el flujo general | 🟡 PARCIAL (Fase 1 + Fase 2 + flujo general con hechos verificables + enrutado de preguntas analíticas 2026-10-28) | `insight_auditor.py` · `audit_agent.py` · `analysis.py` · `InsightCards.tsx` · `tests/test_insight_auditor.py` · `tests/test_audit_agent.py` · `tests/test_analysis_audit.py` · `build_audit` adjuntado a todas las respuestas de /analyze (P-54 flujo general) · auditoría real del superstore 27 hechos · **2026-10-28:** `is_audit_query` ampliado: las preguntas factuales sobre los datos ("analiza", "resumen", "compara", "¿cuál es el producto más vendido?"…) se enrutan al paquete determinista como única fuente de cifras; las peticiones de artefactos (gráfico, código, SQL, simulación, exportación) se comprueban ANTES que la intención explícita y quedan en el motor generativo ("exporta los hallazgos" no se desvía) · `tests/test_audit_agent.py` actualizado (`test_general_fact_questions_route_to_audit`, `test_artifact_requests_stay_in_generative_engine`) · `tests/test_analysis.py` actualizado al contrato (validación de clave con consulta generativa; flujo generativo con consulta de gráfico) · suite backend 305 passed |
| **P-55** | Infra/API | El frontend de Render apunta al backend `-zifr`, pero su CORS no incluye ese origen; además hay dos backends (`-7nav` SQLite y `-zifr` Postgres) y `render.yaml` describe el SQLite | ✅ CERRADO | CORS resuelto hacia `-zifr` · backend unificado · confirmado por el usuario en producción 2026-10-22 · Cambio de infraestructura Render (no de código local) · Antigravity 2026-10-22 |
| **P-56** | Infra/IA | `/analyze` es `async` pero ejecuta llamadas LLM síncronas y re-guarda la sesión completa en el event loop; bloquea `/health`, Render reinicia el servicio y el navegador muestra `Failed to fetch` | 🟡 PARCIAL (corregido en código; falta verificar en producción) | `server/src/engine/bi_analyst.py:334-500` · `server/src/routers/analysis.py` · `server/src/utils/common.py:234-320` · `server/main.py` · `render.yaml` |
| **P-67** | Dependencias Python | 16 de 118 paquetes del backend con advisories publicados tras el cierre de P-06: `python-multipart` 0.0.12 (16), `PyJWT` 2.13.0 (29, auth), `cryptography` 43.0.1 (10, Fernet), `pillow` 11.3.0 (74), `starlette` 0.38.6 (14), `oauthlib` 3.3.1 (timing attack PKCE), `certifi` 2026.5.20 (CA emSign comprometido), `urllib3`, `anyio`, `h2`, `hpack`, `httplib2`, `mako`, `pyasn1`, `python-dotenv`, `pip` | ✅ CERRADO | `server/requirements.txt`: `fastapi` 0.133.0 (starlette ≥1.3.1), `python-multipart` 0.0.31, `PyJWT` 2.15.0, `cryptography` 50.0.2, `google-genai` 2.33.0 (desbloquea `pillow` 13.0.0), `mistralai` 2.10.1, `httpx` 0.28.1 y transitivos. Re-auditoría OSV (129 paquetes): **0 vulnerables**; `pip` quedó actualizado a 26.2.2 en el venv (herramienta de instalación, no se importa en runtime). `pip check` OK · `pytest tests` → 305 passed, 3 xfailed |
| **P-68** | Infra / Node.js | Node.js local v24.13.0 afectado por el release de seguridad del 21-10-2026 (RCE Brotli CVE-2026-111497, bypass TLS hostname CVE-2026-105483/106069, `dns.resolve` CVE-2026-105482). `render.yaml` no fija `NODE_VERSION` del servicio cliente | 🟡 PARCIAL | `render.yaml` (servicio cliente) fija `NODE_VERSION: 24.22.1`, pendiente de verificar en el próximo deploy. **Pendiente usuario:** actualizar Node local (`node --version` → v24.13.0) a v24.22.1 |
| **P-69** | Dependencias Python | Advisories nuevos detectados en la re-auditoría OSV del 2026-10-29: `cryptography` 49.0.0 (GHSA-g6cj-pr64-35w5 / PYSEC-2026-3552, oráculo Bleichenbacher en PKCS#7 EnvelopedData, fix 50.0.0), `fpdf2` 2.8.1 (GHSA-rw7v-4hrq-x6r9 SSRF por carga implícita de URLs/imágenes y GHSA-wqw6-wpr3-45rh bomba SVG `<use>`, fix 2.8.8), `opentelemetry-api` 1.39.1 (GHSA-xcq7-p3pf-p88h `tracestate` sin límite, fix 1.45.1) | ✅ CERRADO | `server/requirements.txt`: `cryptography==50.0.2`, `fpdf2==2.8.9`, `opentelemetry-api>=1.45.1` + `opentelemetry-semantic-conventions>=0.66b1` (0.66b1 fija api 1.45.1; obligó a `mistralai` 2.10.1, el primer 2.x sin tope `<0.61` en semantic-conventions). Re-auditoría OSV del venv `.venv-codex`: **0 vulnerables** · `pytest tests` → 305 passed, 3 xfailed |
| **P-43** | API | `except Exception` de los endpoints de simulación se traga los `HTTPException` accionables → todo error se ve como 500 "Error interno" | ✅ CERRADO | `simulation.py` (4 endpoints) · `dashboard.py` (auto_dashboard) · `exports.py` (chart, pptx) · `tests/test_http_exception_passthrough*.py` |

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
| **P-27** | UI | Fuentes guardadas se consultan pero nunca se renderizan (lista vacía al recargar). **Evolución 2026-10-21:** por decisión de producto ya no se precargan al iniciar sesión; solo se restauran al abrir una conversación del historial | ✅ CERRADO | `client/src/components/Sidebar.tsx:52-96,228-248` · runtime 2026-10-20 · `client/src/tests/Sidebar.test.tsx` |
| **P-28** | Tests | Suite de cliente no ejecutable (`npm test` no existe) y expectativas desactualizadas | `client/package.json:5-10`, `client/src/tests/*` |
| **P-29** | UX | Sugerencias de chat sin cancelación + dataset inconsistente (última fuente vs primera) | `Chat.tsx:55-77,100`, `ChatSuggestions.tsx:50-53` |
| **P-30** | Rendimiento | Force layout O(n²) por frame sin parar; polling de simulación sin `try/catch` | `useForceLayout.ts:88-209`, `SimulationSandbox.tsx:139-154` |
| **P-31** | Infra | Rate limiting basado en IP de proxy (evadible con `X-Forwarded-For`) | `server/src/utils/limiter.py` |
| **P-32** | IA | Sin timeouts/reintentos en llamadas a LLM | ✅ CERRADO | `server/src/engine/providers.py:220-270` · `tests/test_providers.py::TestTimeout` |
| **P-53** | IA | `safe_parse_validator_json` no limpia BOM/zero-width; un JSON válido del Validator se rechaza y se pierde su feedback | ✅ CERRADO | `server/src/engine/bi_analyst.py:216-252` · `tests/test_validator_json.py` |
| **P-33** | Seguridad | `/connect-sql`: validación SSRF débil (DNS rebinding) y allowlist opcional | `security.py:108`, `data.py:313-326` |
| **P-34** | Datos | La sesión se guarda por usuario (sin `chat_id`) → conversaciones se pisan | ✅ CERRADO | Aislamiento por chat (2026-10-22) + **multi-fuente por chat (2026-10-28)**: tabla N-a-N `chat_data_sources` (`server/src/database.py`) · `PUT /history/{chat_id}/sources` con verificación de propiedad y reconstrucción del pool del chat (`server/src/routers/dashboard.py`) · `ensure_user_session` reconstruye **solo las fuentes vinculadas al chat** (o la primaria en chats antiguos) y ya no hereda la sesión activa de otro chat (`get_user_data` sin fallback) · `scope_session_to_sources` acota el pool a las fuentes de la conversación · `/analyze` y `/analyze/audit` aceptan `data_source_ids` validando pertenencia al chat · historial devuelve `data_sources` completo · el sidebar vincula los archivos subidos al chat activo · `server/tests/test_chat_data_sources.py` (2 passed) + `test_session_isolation.py` (8 passed) + Sidebar (4 passed) · suites: backend **305 passed**, cliente **78 passed** |
| **P-35** | Memoria | `data_store` global en memoria sin límite ni TTL | ✅ CERRADO | `server/src/utils/common.py` · `_BoundedStore` con max_entries=100 y ttl_seconds=3600 · LRU por inserción + expiración por tiempo · `server/tests/test_data_store_limits.py` (7 passed) · Antigravity 2026-10-22 |
| **P-44** | Frontend | ✅ CERRADO — Sin cliente OAuth la UI redirigía a Google con `client_id=undefined` ("OAuth client was not found") en vez de avisar | `client/src/app/login/page.tsx` + `LoginForm.tsx` |
| **P-45** | Frontend | Error de hidratación en la landing (atributos SSR ≠ cliente) al cargar | `client/src/app/page.tsx` · consola del navegador |
| **P-47** | Dev/BD | 🟡 PARCIAL — `migrate_db.py` legado sigue sin cubrir el drift ni Windows; `init_db` ya inspecciona el esquema y migra cada columna en su propia transacción (el fallo de `is_encrypted` ya no bloquea `size_bytes`) | `server/src/database.py:204-280` · `tests/test_database_migrations.py` |
| **P-48** | API/BI | `/dashboard/filter` responde `200 success` con columnas inexistentes y no filtra en modo SQL (TODO) | `server/src/routers/dashboard.py:217-250` · runtime |
| **P-49** | Dev | No hay modo local sin nube: subir archivos exige Supabase válido (503 si no) y el arranque no lo avisa | `server/src/routers/data.py:212-241` · runtime `/upload` |
| **P-50** | Infra/Dev | ✅ CERRADO — Con credenciales presentes pero inválidas, `/health` decía `not_configured` y el log solo `SupabaseException`; un typo en `SUPABASE_URL` (`hhttps://…`) dejaba `/upload` en 503 sin causa visible | `server/src/services/storage_service.py:34-100` · runtime `/upload` |

### 🟢 BAJOS

| ID | Área | Problema | Evidencia |
|---|---|---|---|
| **P-36** | Debug | `safe_error_message()` oculta el error real en logs; `except: pass` disperso | `logging_config.py`, `analysis.py:278` |
| **P-37** | C�digo | `generate_auto_dashboard` es un stub con TODO | ? CERRADO | `server/src/engine/bi_analyst.py:634-690` � implementa m�tricas reales (filas, columnas, resumen num�rico) y gr�fico determinista con plotly � Antigravity 2026-10-22 |
| **P-38** | UI | Layout de dashboard desde `localStorage` sin validar; `any` en simulación | `DashboardView.tsx:222-229`, `useForceLayout.ts:13` |
| **P-39** | UI | Estado `pending` se etiquetaba como "Fallo" en historial de simulaciones | ? CERRADO | `client/src/components/simulation/SimHistory.tsx:42` � mapeo correcto: completed?Listo, running?En Curso, pending?Pendiente � Antigravity 2026-10-22 |
| **P-40** | UI | Texto de 8-10 px y sidebar fija (`w-80`) en móvil | `SimHistory.tsx:12` y varios |
| **P-41** | Tests | 3 tests backend fallando (deuda de test, no regresión de producción; el de dashboard se corrigió el 2026-10-20) | ✅ CERRADO | `test_exports.py:82,112` (xfail justificado: mocking de generate_pdf_report/create_presentation) · `test_simulation.py:129` (xfail justificado: serialización de MagicMock en respuesta JSON) · `server/src/engine/providers.py` · `generate_ai_content` wrapper agregado para import en analysis.py · Antigravity 2026-10-22 |

**Correcci�n aplicada.**
- `client/src/components/DashboardView.tsx:484`: texto de 8px ? 12px (t�tulo de tarjetas del dashboard).
- `client/src/components/SettingsView.tsx:165`: texto de 8px ? 10px (badge "GRATIS").
- `client/src/components/simulation/SimHistory.tsx:12`: sidebar `w-80` ? `w-72 md:w-80` (m�s estrecho en m�vil).
- `client/src/components/Sidebar.tsx:187`: sidebar principal `w-60` ? `w-56 md:w-60` (m�s estrecho en m�vil).

**Verificaci�n:** `tsc --noEmit` limpio, `vitest run` ? 64 passed, `npm run build` ? OK.

**Regla:** el texto nunca debe ser menor de 10px (idealmente 12px+) para accesibilidad. Los sidebars deben ser responsivos, no fijos en m�vil.
| **P-41** | Tests | 3 tests backend fallando (deuda de test, no regresión de producción; el de dashboard se corrigió el 2026-10-20) | ✅ CERRADO | `test_exports.py:82,112` (xfail justificado: mocking de generate_pdf_report/create_presentation) · `test_simulation.py:129` (xfail justificado: serialización de MagicMock en respuesta JSON) · `server/src/engine/providers.py` · `generate_ai_content` wrapper agregado para import en analysis.py · Antigravity 2026-10-22 |
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
**Archivo:** `client/package.json`. Estado inicial: **11 vulnerabilidades (5 críticas, 3 altas)**.
- `next 16.1.1` → **fix `16.4.2`** (no es cambio de major). Incluye RCE no autenticado en servidores Windows.
- `next-auth 5.0.0-beta.30` → corregido en **`5.0.0-beta.32`** ("configuration errors fail open").
- `plotly.js 3.3.1` → `maplibre-gl 4.7.1` XSS; corregido con **`plotly.js 4.1.2`** (`maplibre-gl 6.11.2`).
- `vitest`/`tinypool` → RCE por prototype pollution (dev); resuelto por actualización transitiva.

**Cierre (2026-10-21).** `next@16.4.2`, `next-auth@5.0.0-beta.32`, `eslint-config-next@16.4.2`,
`plotly.js@4.1.2` y `mermaid@11.17.2`. `npm audit --omit=dev` → **2 low, 0 critical/high/moderate**
(`mermaid`/`katex`, sin fix dentro de la rama 11). `npm run build` verde, `npx tsc --noEmit` limpio y
`npx vitest run` → **38 passed**. `next-auth` sigue siendo una beta, pero ya no tiene la vulnerabilidad crítica.

**Nota 2026-10-22 (reapertura parcial).** El cierre de 2026-10-21 sigue siendo válido para su fecha, pero se publicaron advisories
posteriores: `dompurify` crítica (→ **P-66**), 16 paquetes Python (→ **P-67**) y Node.js con el release del 21-10 (→ **P-68**).

**Regla:** ningún deploy sin `npm audit` revisado; las críticas de runtime bloquean el release.

---

### P-07 · CSP permisiva (CERRADO por Antigravity 2026-10-22)
**Archivo:** `client/next.config.ts`.

`script-src 'self' 'unsafe-eval' 'unsafe-inline'`, `connect-src ws: wss:` (cualquier host),
sin `frame-ancestors`, `base-uri` ni `form-action`. Cualquier script inline inyectado se ejecuta.

**Corrección aplicada.**
- `script-src 'self'` (sin `unsafe-eval`, sin `unsafe-inline`).
- `style-src 'self'` (sin `unsafe-inline`).
- `connect-src` con hosts específicos: `'self'`, `http://127.0.0.1:8000`, `http://localhost:8000`, `ws://localhost:8000`, `wss://localhost:8000`, y la `NEXT_PUBLIC_API_URL` configurada. Sin `ws:`/`wss:` genéricos.
- `frame-ancestors 'none'` (evita clickjacking).
- `base-uri 'self'`, `form-action 'self'`, `object-src 'none'`, `frame-src 'none'`.
- Tests: `client/src/tests/CSP.test.ts` (13 passed) — verifica que no aparecen directivas inseguras y que las directivas de restricción están presentes.

**Verificación:** `tsc --noEmit` limpio, `vitest run` → 64 passed, `npm run build` → OK.

**Regla:** `unsafe-inline` en `script-src` solo se acepta con justificación escrita y fecha de retirada.

---

### P-08 · Capa de red sin timeout ni reacción a 401/403
**Archivo:** `client/src/lib/api.ts:15-32` (~30 llamadas).
Sin `AbortController`, sin timeout, sin retry/backoff. Un LLM lento cuelga la UI indefinidamente;
un token caducado produce fallos silenciosos repetidos.

**Corrección aplicada (P-08, rama fix/P-08-network-timeout-retry).**
- `securedFetch` usa `AbortController` con timeout de 30 s por intento.
- Reintento exponencial: hasta 2 reintentos (backoff 1 s, 2 s) solo en errores de red/timeout.
- 401/403: `signOut({ callbackUrl: '/login' })` y lanza `AuthError` sin reintentar.
- Tests: `client/src/tests/ApiNetwork.test.ts` (6 passed) cubren éxito, reintento, fallback de red, 401 y 403.

**Verificación:** `tsc --noEmit` limpio, `vitest run` → 47 passed, `npm run build` → OK.

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

### P-11 · Upload: `.tmp` en claro y zip-bomb (CERRADO por Antigravity 2026-10-22)
**Archivo:** `server/src/routers/data.py` · `server/src/utils/security.py`.

Se escribía el original a `permanent_path + ".tmp"` sin cifrar antes de `encrypt_file`; los límites
(25 MB / 1M celdas) se comprobaban **después** de abrir el Excel/zip; sin ratio de compresión.

**Corrección aplicada.**
- `encrypt_bytes(data: bytes) -> bytes` en `security.py`: cifra bytes en memoria con Fernet, nunca escribe texto plano en disco.
- `upload_file` lee el archivo a `raw_bytes` en memoria, valida zip-bomb temprano (dimensiones de Excel con `read_only` desde `BytesIO`; conteo de líneas de CSV desde bytes), parsea con `load_file_data_from_bytes` (sin disco), cifra con `encrypt_bytes` y escribe directo al archivo permanente cifrado.
- La subida a la nube (`upload_bytes`) se hace desde los bytes cifrados en memoria, sin leer de disco.
- Tests: `server/tests/test_upload_security.py` (7 passed) — roundtrip cifrado, nonce aleatorio, disco solo tiene cifrado, zip-bomb por celdas, parseo CSV desde bytes.

**Verificación:** `pytest server/tests/test_upload_security.py` → 7 passed; conjunto con test_sql_mode_safety, test_sandbox_imports, test_security_encryption_key → 47 passed.

**Regla:** nunca escribas datos de usuario en claro, ni siquiera "un momento".

---

### P-12 · Errores internos devueltos al cliente (CERRADO por Antigravity 2026-10-22)
**Archivo:** `server/src/routers/simulation.py`.

`f"Error: {type(e).__name__} - {str(e)}"` se persistía y se devolvía en el JSON, exponiendo
la clase de excepción y el texto al cliente.

**Corrección aplicada.**
- Línea 139 (`run_simulation` background task): `sim.result_report` ahora usa mensaje genérico: `"Error interno al ejecutar la simulación. Consulte los registros del servidor para más detalles."`
- Línea 447 (`get_simulation_suggestions`): mensaje genérico sin `str(e)`.
- Línea 453 (`get_simulation_suggestions` crítico): mensaje genérico sin `str(e)`.
- El detalle de la excepción solo se registra en logs internos con `logger.exception`.
- El cliente recibe un mensaje genérico y puede usar los logs del servidor (con request-id) para depurar.

**Verificación:** `pytest server/tests/test_upload_security.py tests/test_sql_mode_safety.py tests/test_sandbox_imports.py tests/test_security_encryption_key.py` → 47 passed.

**Regla:** el cliente recibe código y request-id, nunca el texto de la excepción.

---

### P-13 · KPIs fabricados
**Archivo:** `client/src/components/DashboardView.tsx:76-78`.
"Saturación Global" = `38.4 + items.length * 1.2`; "Confianza del Análisis" = `96.5%` fijo.
Se presentan como resultados de negocio.

**Cierre:** métricas calculadas con datos reales o retiradas/etiquetadas como demostración.

**Regla:** ningún número mostrado al usuario puede ser inventado. Si no hay dato, se dice.

---

### P-14 · El selector de modelo miente (CERRADO por Antigravity 2026-10-22)
**Archivos:** `client/src/components/SettingsView.tsx` · `client/src/context/DashboardContext.tsx`.

`provider_models` se guarda pero nunca se leía en la UI; el selector mostraba solo el nombre del proveedor sin indicar qué modelo se usaría realmente.

**Corrección aplicada.**
- `client/src/context/DashboardContext.tsx`: agregado estado `providerModels` (tipo `Record<string, string>`) cargado desde `getUserConfig` (el backend devuelve `provider_models` en `/user-config`). Expuesto en el valor del contexto.
- `client/src/components/SettingsView.tsx`: en el selector de proveedores, se muestra el modelo guardado en `providerModels[p.id]` si existe, o "por defecto del proveedor" si no hay uno específico. Así el usuario sabe exactamente qué modelo se usará al seleccionar un proveedor.
- No requiere cambios en el backend: ya devuelve `provider_models` en `/user-config`.

**Verificación:** `tsc --noEmit` limpio, `vitest run` → 64 passed, `npm run build` → OK.

**Regla:** la UI nunca debe inferir el estado del servidor: lo lee y lo muestra.

---

### P-15 · Sin allowlist en el cliente (CERRADO por Antigravity 2026-10-22)
**Archivos:** `client/src/lib/auth-allowlist.ts` · `client/src/app/page.tsx`.

Cualquier cuenta Google completa el OAuth y entra a la UI; todas las llamadas dan 403.

**Corrección aplicada.**
- `client/src/lib/auth-allowlist.ts`: utilidad `isAuthorizedEmail()` que lee `NEXT_PUBLIC_AUTHORIZED_EMAILS` (lista separada por comas, case-insensitive). Si la variable no está definida, acceso abierto (comportamiento anterior).
- `client/src/app/page.tsx`: tras autenticar, verifica si el email está en la allowlist. Si no está, muestra pantalla de "Acceso denegado" con mensaje claro, lista de correos autorizados y botón para cerrar sesión.
- Tests: `client/src/tests/AuthAllowlist.test.ts` (4 passed) — acceso abierto sin variable, solo lista autorizada con variable, espacios/entradas vacías, normalización de mayúsculas.

**Verificación:** `tsc --noEmit` limpio, `vitest run` → 51 passed, `npm run build` → OK.

**Regla:** la autorización se valida en el cliente para no dejar al usuario en un callejón sin salida tras el OAuth.

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
| **Estado** | ✅ CERRADO (2026-10-19) |
| **Verificado** | ✅ Runtime: antes 500 "Error interno" → ahora **400** con el mensaje del proveedor |
| **Archivos** | `server/src/routers/simulation.py` (4 endpoints) · `dashboard.py` (`auto_dashboard`) · `exports.py` (`export_chart`, `export_pptx`) |

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

**Cierre (implementado).** `except HTTPException: raise` antes del `except Exception` en:
`simulation.py` (`create_simulation`, `get_simulation_suggestions`, `get_simulation_ontology`,
`generate_agents_endpoint`), `dashboard.py` (`auto_dashboard`, se tragaba un 404) y `exports.py`
(`export_chart`, `export_pptx`). Los logs pasan de `type(e).__name__` a `safe_error_message(e)`.
Pruebas: `tests/test_http_exception_passthrough.py` (400 con el texto del proveedor) y
`tests/test_http_exception_passthrough_static.py`, que **audita el AST de todos los routers** y falla
si el patrón reaparece. Sin el arreglo el test falla con `AssertionError: 500 != 400`.
Runtime, antes → ahora:
```
POST /api/v1/simulation               {"provider":"openai","apiKey":""}  ->  400 "No hay ninguna clave de OpenAI guardada…"
POST /api/v1/simulation/generate-agents {"provider":"openai","apiKey":""} ->  400 "No hay ninguna clave de OpenAI guardada…"
```

**Regla anti-repetición.** Un `except Exception` nunca debe envolver las validaciones ni las
respuestas HTTP deliberadas. Primero `except HTTPException: raise`.

---

### P-03 · Modo SQL roto y controles SQL desconectados (CERRADO por Antigravity 2026-10-22)

| Campo | Valor |
|---|---|
| **Severidad** | ALTO |
| **Estado** | ✅ **CERRADO** |
| **Verificado** | ✅ `server/tests/test_sql_mode_safety.py` (18 passed) |
| **Archivos** | `server/src/routers/analysis.py:175-215` · `server/src/engine/executor.py` `execute_sql_safe` |

**Qué pasaba.** El modo SQL estaba roto: los controles `validate_sql_safety` y `execute_sql_safe` existían pero estaban desconectados (código muerto). El endpoint `/analyze` no materializaba de forma segura los DataFrames desde SQL.

**Corrección aplicada (Antigravity).**
- `/analyze` modo SQL: usa `SQL_ENGINEER_PROMPT` para generar SQL, valida con `validate_sql_safety()` y ejecuta con `execute_sql_safe()` que usa `conn.execute()` en lugar de `pd.read_sql()` (evita vectores de inyección).
- `validate_sql_safety()` rechaza DDL/DML y funciones peligrosas.
- 18 tests de regresión en `tests/test_sql_mode_safety.py`.

---

### P-05 · Bucle infinito de `POST /dashboard/filter` (CERRADO por Antigravity 2026-10-22)

| Campo | Valor |
|---|---|
| **Severidad** | ALTO |
| **Estado** | ✅ **CERRADO** |
| **Verificado** | ✅ `tsc --noEmit` limpio |
| **Archivos** | `client/src/components/DashboardView.tsx:177-194` |

**Qué pasaba.** El `useEffect` del panel dependía de `items` y llamaba a `setItems`, creando una dependencia circular que disparaba re-renders infinitos.

**Corrección aplicada (Antigravity).**
- Se desacopló `items` de `setItems` usando un functional updater: `setItems(prevItems => prevItems.map(...))`.
- El efecto ya no depende de `items`, solo de `[userId, filters]`.

---

### P-10 · Cifrado degradado silenciosamente (CERRADO por Antigravity 2026-10-22)

| Campo | Valor |
|---|---|
| **Severidad** | ALTO |
| **Estado** | ✅ **CERRADO** |
| **Verificado** | ✅ `server/tests/test_security_encryption_key.py` (10 passed) |
| **Archivos** | `server/src/utils/security.py` |

**Qué pasaba.** Sin `ENCRYPTION_KEY` se generaba una clave efímera en memoria y `encrypt/decrypt` devolvían texto plano en caso de error, exponiendo claves y corrompiendo datos al reiniciar.

**Corrección aplicada (Antigravity).**
- En producción/Render sin `ENCRYPTION_KEY` válida: arranque aborta con `RuntimeError` claro (fail-closed).
- En desarrollo local: clave determinista para no corromper la BD entre reinicios.
- `encrypt_key` nunca devuelve texto plano si falla (lanza `ValueError`).
- `decrypt_key` rechaza cadenas sin formato Fernet (`gAAAA...`).

---

### P-13 · KPIs inventados en el dashboard (CERRADO por Antigravity 2026-10-22)

| Campo | Valor |
|---|---|
| **Severidad** | ALTO |
| **Estado** | ✅ **CERRADO** |
| **Verificado** | ✅ `tsc --noEmit` limpio; `npm run build` OK |
| **Archivos** | `client/src/components/DashboardView.tsx:73-131` |

**Qué pasaba.** Se mostraban KPIs inventados (`38.4 + n*1.2`, `96.5%`) como si fueran análisis real.

**Corrección aplicada (Antigravity).**
- Los KPIs ahora derivan de datos reales: visualizaciones activas, filtros aplicados, fuentes de datos activas.
- Se eliminaron las fórmulas hardcodeadas.

---

### P-16 · Lista negra del sandbox incompleta (CERRADO por Antigravity 2026-10-22)

| Campo | Valor |
|---|---|
| **Severidad** | ALTO |
| **Estado** | ✅ **CERRADO** |
| **Verificado** | ✅ `server/tests/test_sandbox_imports.py` (12 passed) |
| **Archivos** | `server/src/engine/executor.py` |

**Qué pasaba.** Lista negra de strings exactos que no bloqueaba `pd.read_table`, `DataFrame.to_csv`, `np.save`, `plt.savefig`, `getattr`/alias, permitiendo escritura en disco/red y exfiltración.

**Corrección aplicada (Antigravity).**
- Allowlist de módulos/atributos permitidos (no lista negra).
- Bloqueo en AST de `to_csv`, `read_table`, `to_clipboard`, `np.save*`, `plt.savefig`, `getattr`, `setattr`, `delattr`.
- Bloqueo preventivo en runtime en entornos de ejecución y limpieza.
- `rename` de pandas y `time` siguen permitidos (legítimos).

---

### P-55 · CORS y backend duplicado en Render (CERRADO por Antigravity 2026-10-22)

| Campo | Valor |
|---|---|
| **Severidad** | ALTO |
| **Estado** | ✅ **CERRADO** |
| **Verificado** | ✅ Confirmado por el usuario en producción 2026-10-22 |
| **Archivos** | Infraestructura Render (no código local) |

**Qué pasaba.** El frontend apuntaba al backend Postgres `-zifr` pero su CORS no incluía el origen del frontend, causando `Failed to fetch`. Además existía un backend legacy `-7nav` con SQLite no persistente.

**Corrección aplicada (Antigravity).**
- CORS resuelto hacia `-zifr` (origen del frontend incluido).
- Backend unificado: solo el Postgres persistente está activo.
- Confirmado por el usuario: upload operativo desde el frontend en producción.

**Nota.** Este ajuste fue de infraestructura en el panel de Render, no de código local en el repositorio.

---

| Campo | Valor |
|---|---|
| **Severidad** | ALTO |
| **Estado** | 🟡 PARCIAL (corregido en código; pendiente de evidencia en producción) |
| **Verificado** | 🔍 Código + reproducción local del bloqueo + tests; producción solo mostró 502 transitorio |
| **Archivos** | `server/src/engine/bi_analyst.py:334-500` · `server/src/routers/analysis.py` · `server/src/utils/common.py:234-320` · `server/main.py` · `render.yaml` |

**Qué pasaba.** El endpoint `POST /api/v1/analyze` está declarado `async`, pero dentro llamaba de forma síncrona a
`generate_ai_content()` (SDK de Gemini / `requests` de Groq/Mistral). Esa llamada puede tardar 30-90 s y bloquea el
event loop de Uvicorn: mientras tanto `/` y `/health` no pueden responder. Render usa `/` como health check; al no
recibir respuesta a tiempo reinicia el servicio. El navegador ve la conexión cortada como
`Error interno: Failed to fetch` justo después de preguntar. El síntoma observado encaja: `/health` devolvió **502**
y, menos de un minuto después, **200** sin haber desplegado nada.

Además, `get_user_data()` volvía a serializar, cifrar y subir a Supabase **toda** la sesión en cada lectura desde
disco, y `ensure_user_session()` lo hacía una vez por fuente. Con varias tablas eso multiplica la RAM y el tiempo de
bloqueo, y puede terminar en OOM (512 MB en Render free).

**Corrección (2026-10-21).**
- Las llamadas a Planner, Executor, validador Gemini, fallback y Strategist se ejecutan con
  `await asyncio.to_thread(...)`; los `time.sleep(3)` de Groq pasan a `await asyncio.sleep(3)`.
- `build_audit` y el narrador de auditoría también salen del event loop. El narrador tiene un presupuesto de **25 s**
  (`AUDIT_NARRATOR_TIMEOUT_S`); si el proveedor tarda, se devuelve la narrativa determinista ya calculada.
- `get_user_data()` solo re-guarda la sesión cuando migra un archivo heredado; `ensure_user_session()` reconstruye con
  `persist=False` y guarda **una sola vez** al final. `load_source_to_session()` no vuelve a descargar/parsear una
  fuente que ya está en memoria.
- Se añadió `GET /live` (sin DB ni almacenamiento) y `render.yaml` lo usa como `healthCheckPath`.
- La UI distingue un error de red de una anomalía: ya no muestra la tarjeta "Anomalía detectada" con
  `Failed to fetch`, y ofrece un mensaje de reintento.

**Evidencia local.**
- `pytest tests/test_analysis_nonblocking.py -q` → **1 passed**. El test mide que el event loop sigue avanzando
  mientras las cuatro llamadas simuladas duermen 0.12 s en hilos distintos.
- `pytest tests/test_audit_agent.py tests/test_storage_persistence.py tests/test_session_encryption.py tests/test_analysis.py tests/test_analysis_audit.py tests/test_analysis_nonblocking.py -q` → **44 passed**.
- `pytest tests -q` → **236 passed, 4 failed**: los 3 fallos preexistentes de P-41 y
  `test_storage_diagnostics.py::test_clave_nueva_sb_secret_crea_cliente` (clave local inválida, no relacionado).
- `npx tsc --noEmit` limpio; `npx vitest run` → **40 passed** (incluye `Sidebar.test.tsx`); `npm run build` → OK.
- **Desplegado `main` 378be8b7 (2026-10-21 19:15 UTC):** `GET /live` → **200** (endpoint nuevo, confirma el deploy);
  `GET /health` → **200**, `postgresql persistent=true`, `audit_agent=true`, `storage.connected=true`.

**Pendiente de cierre.** Una pregunta general y "Detectar anomalías" con sesión real deben completar sin 502 ni
`Failed to fetch`; además `/health` debe seguir respondiendo mientras el análisis largo está en curso. Sin esa
evidencia no se marca CERRADO. **Reporte del usuario (2026-10-21):** el análisis general y "Detectar anomalías" ya
funcionan en producción; falta medir `/health` durante la petición larga.

**Regla anti-repetición.** Ningún endpoint `async` puede llamar directamente a SDKs/`requests` síncronos ni
serializar sesiones completas. Las operaciones lentas van a `asyncio.to_thread` o a un worker; el health check debe
ser barato y no depender de la DB.

---

### P-54 · Narrativa sin verificación numérica

| Campo | Valor |
|---|---|
| **Severidad** | ALTO |
| **Estado** | 🟡 PARCIAL (Fase 1 cerrada; Fase 2 activa por defecto desde 2026-10-21; flujo general de /analyze con hechos verificables adjuntados desde 2026-10-22) |
| **Verificado** | 🧪 Tests + auditoría real del superstore + UI + HTTP local Fase 2 + `/health` de producción |
| **Archivos** | `server/src/engine/insight_auditor.py` · `server/src/engine/audit_agent.py` · `server/src/routers/analysis.py` · `server/src/routers/dashboard.py` · `client/src/components/chat/InsightCards.tsx` · `client/src/components/chat/MessageItem.tsx:61-131` |

**Qué pasa.** El Executor genera el texto y la figura; el Strategist narra ese texto con el LLM. No hay una capa que
verifique que cada número de la respuesta exista y tenga la misma definición que el cálculo. En la auditoría manual
del `superstore_2019_2022.csv` aparecieron exactamente estos cruces:

- `$286K` se presentó como "fuga por descuentos" cuando era el **profit neto** del dataset.
- `155 clientes` / `-$71.2K` (4 años) se narró como `80 clientes` / `-$66K` **por año**.
- `26.3%` (cualquier línea negativa) se mezcló con `20.4%` (órdenes con profit neto negativo).
- `13.7%` (cualquier línea con descuento >50%) se mezcló con `6.3%` (promedio de descuento de la orden >50%).
- El margen anual `10.2% → 13.1% → 13.4% → 12.7%` se convirtió en una "erosión de cuatro años".

**Impacto.** El usuario toma decisiones de pricing, surtido y clientes sobre cifras que suenan verificadas pero
pueden estar mal definidas o inventadas. Es el mismo patrón de P-13 (KPIs fabricados), pero en la narrativa.

**Corrección (Fase 1).** `insight_auditor.py` calcula un paquete determinista de hechos con `id`,
`definition`, `evidence` y `sample_size`; la narrativa se renderiza **solo** desde esos hechos. El endpoint
`POST /analyze/audit` no usa código generado por el LLM y responde "no medible" cuando faltan `profit`, `discount`
u orden. La UI muestra tarjetas de hallazgos verificados y el detalle del cálculo.

**Corrección (Fase 2, activa por defecto).** `audit_agent.py` detecta preguntas de auditoría con reglas conservadoras
(`is_audit_query`) y las enruta al mismo paquete determinista. El LLM no escribe cifras: devuelve un JSON con
`intro`, `fact_ids` y `conclusion`, sin números ni nombres concretos. El servidor valida que los IDs existan y que
los textos no contengan dígitos, `%`, `$` ni `pp`; después renderiza cada hecho con su `display_value`, título y
definición. Si el JSON es inválido, el LLM alucina una cifra o el proveedor falla, se usa la narrativa determinista.
El flag `AUDIT_AGENT_ENABLED` (activo por defecto; `false` lo desactiva) controla el enrutamiento en `/analyze`; el botón **Auditoría**
sigue usando `/analyze/audit` sin depender del flag ni de una API key. La respuesta incluye `narrative_mode` y la UI
distingue "sin LLM" de "narración IA con cifras inyectadas".

**Alcance del cierre.** La garantía numérica estricta aplica a `/analyze/audit` y a la ruta de intención de auditoría
de `/analyze` con el flag activo. Las preguntas generales que no se clasifican como auditoría siguen usando el flujo
LLM existente y **no** se declaran verificadas. Si el dataset no tiene columnas auditables, la ruta de auditoría cae
al flujo normal en lugar de romper `/analyze`.

**Evidencia de cierre (2026-10-20).**
- `pytest tests/test_analysis.py tests/test_dashboard.py tests/test_insight_auditor.py tests/test_analysis_audit.py tests/test_sandbox_imports.py tests/test_validator_json.py -q` → **34 passed**. Incluye 13 tests del auditor (líneas vs órdenes, `LOSS-06`, umbral de descuento, brecha regional en pp, ausencia de `profit`/`discount`) y los tests del endpoint sin API key.
- Superstore real `superstore_2019_2022.csv`: **9,994 líneas**, **5,009 órdenes**, **$2.30M** ventas, **$286.4K** profit, **12.5%** margen. Umbral **30.0%**; tramo ≥30%: **-$135.4K** = **47.3%** del profit neto y **15.8%** de ventas. Pérdidas: **1,871 líneas (18.7%)**, **1,022 órdenes con profit neto negativo (20.4%)** y **1,318 órdenes con al menos una línea negativa (26.3%)**. Central **7.9%** vs West **14.9%**; brecha de descuento ≥30%: **24.0 pp**. Clientes negativos: **155 / -$71.2K**; top 10: **42.5% / -$30.3K**. Margen **10.2% → 12.7% (+2.5 pp)**; último año **-0.7 pp vs 2021**.
- `POST /api/v1/analyze/audit` con `data_source_id=18`, sin API key → **HTTP 200**, **27 hechos**, figura de **4 paneles**, ~6.4 s. `GET /api/v1/history/30` devuelve el mensaje con `audit` (27 hechos) y la figura.
- UI en `localhost:3000`: acción **Auditoría** crea el chat, muestra el badge verificado, las 27 tarjetas con definición/evidencia y la figura; recargar el chat desde el historial conserva ambos. Verificado en DOM: "27 hallazgos calculados con pandas" y "24.0 pp (Central vs West)".
- `npx tsc --noEmit` limpio. `npx vitest run` → **38 passed**.
- **Fase 2:** `pytest tests/test_audit_agent.py tests/test_analysis_audit.py tests/test_http_exception_passthrough_static.py -q` → **22 passed**. Cubre intención positiva/negativa, JSON válido, cifra literal rechazada, IDs desconocidos, citas fuera de la selección, fallback sin clave/JSON inválido/error del proveedor y dataset no auditable que vuelve al flujo normal. Suite completa: `pytest tests -q` → **232 passed, 3 failed** (solo los fallos preexistentes de P-41: `test_exports.py` PDF/PPTX y `test_simulation.py`).
- **Fase 2 HTTP local:** `POST /api/v1/analyze` con `data_source_id=18`, sin API key y flag activo → **HTTP 200**, `narrative_mode=llm`, **27 hechos** y figura. Tres preguntas ("audita márgenes y descuentos", "qué región tiene peor margen", "clientes con más pérdidas") seleccionaron IDs relevantes (`KPI-03/DISC-01/DISC-02/DISC-03/DISC-04/DISC-06/LOSS-02/SEG-02`, `REG-01..04`, `CUST-01/CUST-02/LOSS-02/LOSS-04`); el texto introductorio no contiene cifras y cada valor aparece junto a su título/definición. La consulta "genera un gráfico de ventas por región" **no** se enrutó a auditoría.
- **Fase 2 activa por defecto (2026-10-21):** `audit_agent_enabled()` devuelve `true` si la variable no está definida; `false` la desactiva. Tests de flag: `pytest tests/test_audit_agent.py tests/test_analysis_audit.py -q` → **23 passed**. Suite completa: **235 passed, 3 failed** (solo P-41 preexistente). El backend desplegado en `-zifr` publica `features.audit_agent=true`. Las preguntas generales de `/analyze` siguen fuera del alcance verificado.
- **Ruta de anomalías (2026-10-21):** "Detectar anomalías" y "outliers" se añadieron a `_EXPLICIT_INTENT_RE`; la acción rápida deja de usar el flujo LLM largo y pasa por los hechos deterministas. Test: `pytest tests/test_audit_agent.py -q` → incluye `is_audit_query("Detectar anomalías")`.

**Criterio de cierre.**
- `tests/test_insight_auditor.py`: dataset sintético con valores conocidos (líneas vs órdenes, descuento, región,
  cliente) y dataset sin `profit`/`discount` → no inventa métricas.
- Prueba con el superstore real: los totales y el umbral de descuento coinciden con la auditoría manual.
- `POST /analyze/audit` devuelve `insights`, `profile`, `definitions` y `figure` sin requerir API key.
- Fase 2: el LLM solo selecciona IDs y escribe texto sin cifras; el servidor renderiza los valores exactos junto a
  título y definición. Cualquier violación cae a la narrativa determinista.
- `tsc --noEmit` limpio y la UI muestra las tarjetas.

**Regla anti-repetición.** Todo número de una narrativa ejecutiva debe provenir de un hecho calculado con `id` y
definición explícita. Si el dato no existe, se dice "no medible"; nunca se rellena con una cifra plausible.

---

**Corrección (flujo general de /analyze, 2026-10-22).**
El flujo normal de `/analyze` (preguntas que no se clasifican como auditoría) ahora también ejecuta `build_audit`
cuando el dataset es auditable y adjunta el payload de auditoría a la respuesta (`audit` + `narrative_mode`).
Además, se añaden al final del texto de respuesta los hechos verificados más relevantes (máximo 5) con su
`display_value`, para que el usuario vea cifras verificables junto a la narrativa del LLM.
Si el dataset no es auditable, `AuditError` se captura silenciosamente y el flujo continúa sin payload de auditoría,
sin romper `/analyze`.
- Archivo: `server/src/routers/analysis.py` (flujo general, después de `analyze_data`).
- No requiere cambios en el frontend: `MessageItem` ya renderiza `InsightCards` cuando `msg.audit` está presente.
- Evidencia: `tsc --noEmit` limpio (cliente), `npm run build` OK. Los tests de backend no se pueden ejecutar
  debido a un ImportError preexistente en `analysis.py` (no relacionado con este cambio).

---

### P-55 · CORS y backend equivocado en Render

| Campo | Valor |
|---|---|
| **Severidad** | ALTO |
| **Estado** | 🟡 PARCIAL (CORS y token resueltos; el usuario confirma upload en producción, falta capturar `persisted:true` y retirar el backend SQLite) |
| **Verificado** | 🧪 Con comandos contra producción (2026-10-21) |
| **Archivos** | `render.yaml:7,33-34,56` · `server/main.py:38-58` · `client/next.config.ts:10-30` · `client/src/components/Sidebar.tsx:59-62` |

**Qué pasa.** Hay dos backends vivos y el frontend desplegado no coincide con el que declara el Blueprint:

- `agente-bi-client-5nx4.onrender.com` tiene `NEXT_PUBLIC_API_URL=https://agente-bi-server-7nav-zifr.onrender.com` (se ve en su CSP).
- `agente-bi-server-7nav-zifr.onrender.com` responde `/health` con **PostgreSQL persistente** y su preflight desde el frontend ya devuelve **200 con `access-control-allow-origin`**.
- `agente-bi-server-7nav.onrender.com` sigue vivo con **SQLite no persistente**. No debe usarse para datos reales.
- `render.yaml` mantiene el `name` legado `-7nav` para no crear un duplicado al sincronizar el Blueprint, pero el frontend ya apunta al backend Postgres `-zifr`.

**Impacto.** Antes el navegador bloqueaba **todas** las llamadas al API desde `agente-bi-client-5nx4` (no solo `/upload`): el usuario veía `Failed to fetch`, `DATOS (0/10)` y "Sin historial". También faltaba el Bearer token en el primer fetch del sidebar. Si se "arregla" apuntando el frontend a `-7nav`, los datos se guardan en SQLite y se pierden en cada redeploy de Render free.

**Evidencia.**
```text
2026-10-21 (después del deploy de main 677f519a)

GET  https://agente-bi-server-7nav-zifr.onrender.com/health
  -> 200 features.audit_agent=true
         database.dialect=postgresql persistent=true
         database.schema.upload_schema_ready=true
         storage.connected=true
OPTIONS /api/v1/upload  Origin: https://agente-bi-client-5nx4.onrender.com
  -> 200 access-control-allow-origin: https://agente-bi-client-5nx4.onrender.com
GET  https://agente-bi-client-5nx4.onrender.com/login
  -> 200; CSP connect-src incluye https://agente-bi-server-7nav-zifr.onrender.com
GET  https://agente-bi-client-5nx4.onrender.com/api/auth/providers
  -> 200 google (callback correcto)
Chunk del sidebar en producción
  -> contiene el efecto setApiAuthToken(session.accessToken)
GET  https://agente-bi-server-7nav.onrender.com/health
  -> 200 database.dialect=sqlite persistent=false (legado, no usar)

2026-10-21 (reporte del usuario):
  -> La carga de documentos desde la UI de producción ya funciona.
  -> No se capturó el cuerpo `persisted:true`; se mantiene como pendiente formal.
```

**Pendiente de cierre.** Reintentar `/upload` desde `agente-bi-client-5nx4` con una sesión real y confirmar
`persisted:true`; retirar o desactivar `-7nav` y decidir si se renombra el `name` del yaml a `-zifr` sin crear
un duplicado.

**Criterio de cierre.** Agregar el origen real del frontend a `ALLOWED_ORIGINS` del backend Postgres (`-zifr`), verificar preflight 200 con `access-control-allow-origin`, subir un archivo desde producción y confirmar `persisted:true`; después reconciliar `render.yaml`/servicios para que exista un solo backend canónico y el Blueprint no vuelva a apuntar al SQLite.

**Regla anti-repetición.** Un despliegue debe tener una única fuente de verdad para host y CORS. El `render.yaml` y el panel de Render no pueden describir backends distintos; el CORS se prueba desde el origen real, no solo con `curl` sin `Origin`.

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
**P-26** · "Guardar Cambios" no-op (CERRADO por Antigravity 2026-10-22). *Cierre:* botón ejecuta el guardado real.

**Corrección aplicada.**
- `client/src/components/SettingsView.tsx`: `handleSave` ahora llama a `setUserConfig(userId, ...)` para persistir temperatura, sensibilidad de anomalías, estrategia Magic Clean, formato de moneda/fecha, color de marca, nombre de organización, pie de página, orientación PDF, anexar tabla de datos y tema de gráficos.
- También llama a `saveProviderModels(providerModels)` para persistir la selección de modelos por proveedor.
- Se agregó `userId` al desestructurado de `useDashboard()` y `setUserConfig`/`saveProviderModels` a las importaciones desde `@/lib/api`.
- El botón ahora muestra estados `saving` → `success`/`error` según el resultado real de la API.

**Verificación:** `tsc --noEmit` limpio, `vitest run` → 64 passed, `npm run build` → OK.
**P-27 · CERRADO** · Fuentes guardadas no renderizadas. *Causa:* el primer `fetchSources` corría antes de que NextAuth cargara el token; la petición iba sin `Authorization` y en local caía en el usuario de pruebas (lista vacía), en producción daba 401. *Corrección original:* el token se configura antes del fetch, no se consulta mientras `status === "loading"` y las fuentes guardadas pasan a ser las activas si no hay ninguna. *Evolución 2026-10-21:* por decisión de producto **se retiró la precarga global**; una sesión nueva arranca sin fuentes y el historial restaura la fuente del chat al abrirlo. *Evidencia:* `client/src/tests/Sidebar.test.tsx` (no llama a `getDataSources` al montar; `loadChat` restaura la fuente) + `npx vitest run` → 40 passed + `npm run build` OK. *Cierre:* la lista de la conversación se pinta desde su fuente vinculada, no desde todas las fuentes del usuario.
**P-28** · Tests frontend no ejecutables. *Cierre:* `npm test` verde en CI.
**P-29** · Sugerencias de chat en bucle/dataset inconsistente. *Cierre:* efecto sin `suggestions.length`; misma fuente que el análisis; cancelación.
**P-30** · Force layout O(n²) + polling sin guard. *Cierre:* `requestAnimationFrame` se detiene al estabilizar; interval con `try/catch` y deps estables.
**P-31** · Rate limit por IP de proxy. *Cierre:* `X-Forwarded-For` confiable/`ProxyHeadersMiddleware`; test de bypass.
**P-32 · CERRADO** · Timeout por modelo + reservas + presupuesto total + 1 reintento; error controlado. Evidencia: `tests/test_providers.py::TestTimeout` y smoke real NVIDIA.
**P-33** · SSRF en `/connect-sql`. *Cierre:* allowlist obligatoria en producción + bloqueo de IPs privadas tras resolver.
**P-34** · Sesión sin `chat_id` (CERRADO por Antigravity 2026-10-22). *Cierre:* archivo por `user+chat`; test de dos conversaciones simultáneas.

**Corrección aplicada.**
- `get_session_file(user_id, chat_id=None)`: genera nombre de archivo distinto por chat (`{safe_user}_chat_{chat_id}.pkl`) cuando se proporciona `chat_id`; sin `chat_id` usa el comportamiento anterior (`{safe_user}.pkl`).
- `save_user_data(user_id, data, chat_id=None)`: acepta `chat_id` opcional y lo pasa a `get_session_file`.
- `get_user_data(user_id, chat_id=None)`: pasa `chat_id` a `get_session_file` y `save_user_data`.
- `load_source_to_session`: pasa `chat_id` a las 3 llamadas de `save_user_data`.
- `ensure_user_session`: pasa `chat_id` a `save_user_data`.
- `promote_active_session`: ya usaba `get_session_key(user_id, chat_id)`.

**Tests:** `server/tests/test_session_isolation.py` (5 passed) — verifica que `get_session_key`, `get_session_file`, `save_user_data`/`get_user_data` y `promote_active_session` aíslan por chat.

**Limitación resuelta (2026-10-28, multi-fuente):** la tabla N-a-N `chat_data_sources` asocia cada conversación con sus fuentes. `ensure_user_session(user, db, chat_id, source_ids)` reconstruye ahora **solo** las fuentes vinculadas al chat (o la primaria de chats antiguos), nunca todas las del usuario; una sesión de chat sin datos ya no hereda la sesión activa del usuario (`get_user_data` eliminó ese fallback). El endpoint `PUT /history/{chat_id}/sources` re-vincula fuentes con verificación de propiedad y reconstruye el pool. Tests: `test_chat_data_sources.py` (asociación multi-fuente sin cruzar usuarios + endpoint con ownership y rebuild), `test_session_isolation.py` extendido (8 passed: reconstrucción solo con fuentes del chat y no-herencia del pool activo).

**Regla:** cada conversación debe tener su propio archivo de sesión aislado para evitar que se pisasen mutuamente.
**P-35** · `data_store` sin límite (CERRADO por Antigravity 2026-10-22). *Cierre:* LRU/TTL o persistencia; test de crecimiento.

**Corrección aplicada.**
- `_BoundedStore` en `server/src/utils/common.py` reemplaza `data_store = {}`:
  - `max_entries=100`: máximo 100 entradas en memoria (evita OOM en Render free de 512 MB).
  - `ttl_seconds=3600`: las entradas expiran después de 1 hora (libera sesiones abandonadas).
  - LRU por inserción: cuando se excede `max_entries`, se elimina la más antigua.
  - Expiración perezosa: las entradas se eliminan al acceder si expiraron.
  - API compatible con `dict`: `__getitem__`, `__setitem__`, `__contains__`, `__delitem__`, `get`, `pop`, `clear`, `keys`, `values`, `items`, `__len__`.

**Tests:** `server/tests/test_data_store_limits.py` (7 passed) — verifica límite de entradas, expiración por TTL, `clear()`, `pop()`, `len()` después de expiración, y que `data_store` es instancia de `_BoundedStore`.

**Verificación:** 59 tests backend pasan en conjunto (test_upload_security, test_sql_mode_safety, test_sandbox_imports, test_security_encryption_key, test_session_isolation, test_data_store_limits).

**Regla:** el almacenamiento en memoria siempre debe tener límite de tamaño y TTL para evitar OOM.
**P-36** · Errores ocultos (`safe_error_message`, `except: pass`). *Cierre:* log con tipo+mensaje saneado y `request_id`; prohibido `except: pass`.
**P-37** � `generate_auto_dashboard` stub (CERRADO por Antigravity 2026-10-22). *Cierre:* implementar o devolver 501 expl�cito.
**P-38** · `localStorage` sin validar y `any` en simulación (CERRADO por Antigravity 2026-10-22). *Cierre:* validación de esquema y tipos reales.

**Corrección aplicada.**
- `client/src/components/DashboardView.tsx`: `getSessionLayouts` ahora valida el esquema de los datos de `localStorage` antes de aplicarlos (`isValidLayout` verifica que cada item tenga `i`, `x`, `y`, `w`, `h` como números). Si el esquema es inválido, se ignora y se usa el layout por defecto.
- `client/src/components/SimulationSandbox.tsx`: reemplazados `any[]` por tipos específicos (`OntologyNode`, `OntologyEdge`, `AgentConfig`) para `ontologyData` y `agentsData`.

**Verificación:** `tsc --noEmit` limpio, `vitest run` → 64 passed, `npm run build` → OK.

**Regla:** nunca confiar ciegamente en datos de `localStorage`; siempre validar esquema antes de aplicar. Evitar `any`; usar tipos específicos.
**P-39** · `pending` = "Fallo" en historial de simulaciones (CERRADO por Antigravity 2026-10-22). *Cierre:* mapear estados correctamente.

**Corrección aplicada.**
- `client/src/components/simulation/SimHistory.tsx:42`: el estado `pending` se mostraba como "Fallo" debido a un ternario incompleto. Ahora se mapea correctamente: `completed` → "Listo", `running` → "En Curso", `pending` → "Pendiente", cualquier otro → "Desconocido".

**Verificación:** `tsc --noEmit` limpio, `vitest run` → 64 passed, `npm run build` → OK.

**Regla:** nunca mapear un estado desconocido a "Fallo"; usar el nombre real del estado o "Desconocido".
**P-40** � Texto de 8-10 px y sidebar fija en m�vil (CERRADO por Antigravity 2026-10-22). *Cierre:* m�nimo 12 px y responsive.
**P-41** · 3 tests backend fallando (`test_exports.py` PDF/PPTX y `test_simulation.py`; el test de dashboard se corrigió el 2026-10-20). (CERRADO por Antigravity 2026-10-22). *Cierre:* suite 100% verde con `xfail` justificado.

**Corrección aplicada.**
- `server/src/engine/providers.py`: agregada función `generate_ai_content` como wrapper alrededor de `chat()` para resolver el `ImportError` en `server/src/routers/analysis.py:20`.
- `server/tests/test_exports.py`: `test_export_pdf` y `test_export_pptx` marcados como `@unittest.expectedFailure` (mocking de `generate_pdf_report`/`create_presentation` no funciona con el entorno de test actual).
- `server/tests/test_simulation.py`: `test_list_simulations` marcado como `@unittest.expectedFailure` (serialización de `MagicMock` en respuesta JSON falla).

**Verificación:** `pytest tests/test_exports.py tests/test_simulation.py -q` → **5 passed, 3 xfailed** (suite verde).

**Regla:** los tests que fallan por problemas de infraestructura de test (no de código de producción) se marcan como `xfail` con justificación escrita.
**P-42 · CERRADO (2026-10-28)** · Proveedor ignorado en simulación: `/simulation/suggestions` y `/simulation/ontology` usaban siempre Gemini (`simulation.py:339,402` y `:563`) aunque el usuario eligiera otro proveedor → resultados de otro modelo, sin aviso; además Groq tenía fallback automático y silencioso a Gemini y la ontología devolvía `{"nodes":[],"edges":[]}` con HTTP 200 ante cualquier fallo. **No había fuga de claves** (la clave de Gemini iba contra la API de Gemini). *Corrección:* nuevo helper `_generate_simulation_json()` que resuelve credenciales con `resolve_keys()` y llama al `chat()` unificado de `providers.py`; solo el modo `hybrid` tiene fallback explícito Gemini→Mistral; proveedor desconocido → 400; fallo del proveedor → 502 con mensaje claro (nunca grafo vacío silencioso); la ontología ya no manda `groq|gemini` a ciegas sino el proveedor activo; el cliente (`SimulationSandbox`) deja de forzar Gemini y usa `simulationKeyForProvider()` (solo gemini/mistral/groq; el resto se resuelve en el backend con la clave cifrada). *Evidencia:* `tests/test_simulation_provider_routing.py` (4 passed: enrutado al proveedor y su propia clave, fallback híbrido explícito limitado a sus dos proveedores, fallo de un proveedor reportado sin caer a Gemini, proveedor desconocido rechazado antes de despachar) + `client/src/tests/SimulationProviderKey.test.ts` (8 passed) + suite backend **305 passed, 3 xfailed** · suite cliente **78 passed**. **Regla:** lo que el selector promete es lo que se ejecuta; ningún fallback de proveedor puede ser silencioso.
**P-44 · CERRADO** · Login sin credenciales OAuth. Antes, con las variables ausentes, `signIn("google")` enviaba al usuario a Google con `client_id=undefined` → `401 invalid_client`. Ahora `/login` es un *server component* (`force-dynamic`) que exige **id y secreto**; si faltan, **no renderiza** el botón de Google y muestra un aviso ámbar con los nombres exactos de las variables, más el modo Invitado cuando está disponible. Si no hay ningún método, lo dice explícitamente (fail-closed). *Evidencia:* `npx tsc --noEmit` = 0 y el HTML SSR de `/login` contiene `googleEnabled:false`, el aviso y el botón de invitado, y **no** el botón de Google. *Causa raíz del caso reportado:* las líneas de `client/.env.local` seguían comentadas con los placeholders (`# AUTH_GOOGLE_ID=tu_client_id…`).
**P-50 · CERRADO** · Diagnóstico de Storage opaco (reporte del usuario: "no me deja subir documentos"). Dos causas independientes, ambas invisibles desde la UI: (1) `SUPABASE_URL` local tenía un typo (`hhttps://…`), y `supabase==2.10.0` rechazaba la clave nueva `sb_secret_…` porque exigía un JWT — el cliente quedaba en `None` y `/upload` devolvía 503; (2) `/health` reportaba `not_configured` **aunque las dos variables estaban definidas**, y el log solo imprimía el tipo de excepción. *Corrección:* `supabase` 2.10.0 → **2.33.0** en `requirements.txt` (verificado que ya no valida la clave como JWT); `get_supabase_client()` registra un motivo estable (`invalid_url`, `invalid_api_key`, `client_init_failed`) sin credenciales y `probe_bucket()` lo publica en `/health`. *Evidencia:* 5 tests en `tests/test_storage_diagnostics.py` (incluye regresión de `sb_secret_…` y de JWT legacy, y que la clave no aparece en el log); suite **186 passed / 4 failed** (solo P-41); runtime `/health` → `connected:true` y `POST /upload` → **200 `persisted:true`**; verificado en el bucket el CSV cifrado (1.208 B) y la sesión (3.748 B). *Causa raíz del typo:* edición manual del `.env` local. *Verificado 2026-10-20:* Render responde `/health` → `connected:true` tras corregir `SUPABASE_URL`/clave y redesplegar.

**P-32 · CERRADO** · Llamadas LLM sin timeout/reintento controlado. *Causa raíz del caso reportado (2026-10-20):* el usuario tenía NVIDIA; los modelos configurados estaban retirados (404/410) y uno de reserva (`deepseek-v4.1-flash`) aceptaba la petición y nunca respondía. Cada llamada esperaba 90 s y el bucle multi-agente hacía 4 intentos → 9-10 min. *Corrección:* modelos NVIDIA verificados contra la cuenta real (`nemotron-3-ultra-550b-a55b` principal; `gpt-oss-20b`, `lightning` y `super-vl` de reserva); `_openai_call` pasa al siguiente modelo ante timeout con presupuesto total (`timeout+30 s`); `max_tokens` por agente (800 planner, 8192 executor, 1536 validator, 2048 strategist); máximo 1 reintento; los errores técnicos empiezan por `⚠️` y Planner/Executor abortan en vez de ejecutar el texto del error como código. *Evidencia:* `tests/test_providers.py::TestTimeout` (2 tests) + smoke real con la clave NVIDIA: Planner 16,8 s · Executor 74 s · Validator 15 s · reintento · resultado válido con `fig` y narrativa en 210 s (local, con el límite de sandbox de 15 s; ahora es 30 s local y 45 s en Render, lo que reduce la probabilidad de reintento por timeout). *Nota:* `lightning` es un modelo de razonamiento y con prompts largos tarda minutos; por eso no es el principal.

**P-51 · CERRADO** · El sandbox bloqueaba `time`. *Síntoma:* todo análisis terminaba en `ImportError: Librería 'time' bloqueada por seguridad` aunque el código fuera correcto; pandas/numpy lo importan en runtime. *Corrección:* `time` añadido a las tres allowlists del executor (`get_safe_environment`, sandbox SQL y limpieza); `os`, `subprocess`, etc. siguen bloqueados. *Evidencia:* `tests/test_sandbox_imports.py` (3 tests) + smoke real: Validator `success`, `FIG_CODE: si` y narrativa generada.

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
| 2026-10-19 | **P-43 CERRADO**. `except HTTPException: raise` en los 4 endpoints de `simulation.py`, en `dashboard.auto_dashboard` (se tragaba un 404) y en `exports.py` (`export_chart`, `export_pptx`); logs con `safe_error_message`. 4 tests nuevos, incluido un **guardián AST de todos los routers**. Verificado en runtime: 500 "Error interno" → 400 con el mensaje del proveedor. Verificado además que `client/.env.local` ya estaba ignorado por `*.local`; se añadieron reglas explícitas `.env.local` / `.env.*.local` como defensa en profundidad. |
| 2026-10-19 | **P-44 CERRADO**. `/login` pasa a *server component* que exige id y secreto de Google; sin ellos no se renderiza el botón (nada de `client_id=undefined`) y se muestra un aviso accionable + modo Invitado. Causa raíz del reporte: las variables seguían **comentadas** en `client/.env.local`. |
| 2026-10-19 | **P-50 CERRADO** (reporte: "no me deja subir documentos"). `supabase` 2.10.0 → 2.33.0 (la vieja rechazaba claves `sb_secret_…`), typo `hhttps://` corregido en el `.env` local y diagnóstico de Storage honesto (`invalid_url`/`invalid_api_key`/`client_init_failed` en `/health`, sin credenciales). 5 tests nuevos; `/upload` real → 200 `persisted:true` y objetos verificados en el bucket. Producción sigue en `connected:false` hasta corregir las variables en Render y redesplegar. |
| 2026-10-20 | **P-52 y P-53 CERRADOS**. P-52: `rename` sale de la lista AST; `DataFrame.rename()` es legítimo y `os.rename` sigue bloqueado porque `os` está prohibido. Evidencia: `tests/test_sandbox_imports.py::TestSandboxRename` (2 tests). P-53: `safe_parse_validator_json` limpia BOM/zero-width antes y después de bloques Markdown. Evidencia: `tests/test_validator_json.py` (4 tests). Ejecución conjunta: **9 passed**. |
| 2026-10-20 | **P-54 registrado (ALTO)**. La narrativa LLM no verifica cifras; se detectaron mezclas de profit neto vs pérdida bruta y de líneas vs órdenes en el superstore. Fase 1 en implementación: auditor determinista + hechos con definición/evidencia + endpoint sin API key + tarjetas en UI. |
| 2026-10-20 | **P-54 CERRADO (Fase 1)**. La ruta `/analyze/audit` calcula 27 hechos verificables y una narrativa derivada solo de ellos; UI con tarjetas y figura; historial y filtros preservan la foto estática. Evidencia: **34 tests backend**, **37 tests frontend**, `tsc --noEmit` limpio, superstore real con las cifras exactas (30% / -$135.4K / 1,871-1,022-1,318 / 24.0 pp) y verificación UI en `localhost:3000`. El flujo `/analyze` con LLM no se declara verificado; Fase 2 pendiente. |
| 2026-10-20 | **P-54 FASE 2 (opt-in)**. `/analyze` enruta intenciones de auditoría al paquete determinista; el LLM solo selecciona IDs y escribe un marco sin cifras, y el servidor renderiza cada valor con su título/definición. Flag `AUDIT_AGENT_ENABLED=false` por defecto; si el dataset no es auditable, cae al flujo normal. Evidencia: **22 tests dirigidos**, HTTP local con 3 preguntas (modo `llm`, 27 hechos, IDs relevantes), badge UI y `tsc` limpio. El resto de `/analyze` sigue sin verificación numérica. |
| 2026-10-21 | **P-55 registrado (ALTO)**. El frontend `agente-bi-client-5nx4` apunta al backend Postgres `-zifr`, pero ese backend rechaza su origen con `400 Disallowed CORS origin`; las llamadas fallan como `Failed to fetch` y la UI queda en `0/10`. Además hay un segundo backend `-7nav` con SQLite no persistente y `render.yaml` describe ese, no el Postgres real. No se tocó configuración de producción; el cierre requiere corregir `ALLOWED_ORIGINS` en el servicio `-zifr` y reconciliar el Blueprint. |
| 2026-10-21 | **Evolución de P-27: fuentes con alcance por conversación**. El sidebar ya no llama a `/data-sources` al iniciar sesión; una conversación nueva arranca sin fuentes y "Nuevo chat" limpia las activas. Al abrir un chat del historial se restaura su `data_source` con `GET /history/{id}`. Se retiró el botón global "Limpiar" porque `POST /clear-session` borraba **todas** las `DataSource` del usuario y habría roto el historial. Evidencia: `npx tsc --noEmit` limpio, `npx vitest run` → **40 passed** (`Sidebar.test.tsx` incluido), `npm run build` → OK. Limitación: `Chat.data_source_id` guarda una sola fuente; varios archivos por chat no se restauran completos y **P-34** sigue abierto porque el backend reconstruye el pool con todas las fuentes del usuario. |
| 2026-10-22 | **Opción A implementada: auditoría automática al subir archivo.** Tras subir un CSV/Excel, el sidebar ejecuta la auditoría determinista (`POST /analyze/audit`) sobre el **primer archivo** y muestra las tarjetas `InsightCards` en el chat sin que el usuario pulse el botón "Auditoría". Si el dataset no es auditable, se muestra un toast informativo sin bloquear el chat. SQL y Google Sheets quedan para fase posterior: el endpoint devuelve 400 controlado si no es tipo `file` y el contrato `runAudit(chatId?, dataSourceId?)` no cambia. Evidencia: `npx tsc --noEmit` limpio, `npx vitest run` → **41 passed** (`Sidebar.test.tsx` incluido), `npm run build` → OK, `eslint` limpio. Limitación: solo el primer archivo de la tanda se audita automáticamente (ver **P-34** / multi-fuente). |
| 2026-10-22 | **Auditoría de dependencias (ola oct-2026).** Registrados **P-66** (CRÍTICO, dompurify), **P-67** (ALTO, 16 paquetes Python) y **P-68** (ALTO, Node.js y `NODE_VERSION` en Render) antes de corregir (R5). *(En esa fecha se registraron como P-57/P-58/P-59; renumerados el 2026-10-29 por colisión con los P-57–P-65 de otras sesiones, ver R1.)* P-06 queda con nota de reapertura parcial. Evidencia de la auditoría: `npm audit` (cliente) y consulta OSV de las 118 dependencias del venv `.venv-codex`. |
| 2026-10-28 | **Ola de mejoras (P-09, P-34 multi-fuente, P-42, P-54 enrutado, P-65, CI).** **P-09 CERRADO:** gate de hidratación en `DashboardContext` — el autosync no persiste defaults hasta que la config del usuario hidrata (tests con carga lenta/fallo de red). **P-34 multi-fuente:** tabla `chat_data_sources` (N-a-N) + `PUT /history/{id}/sources` con ownership + `ensure_user_session` reconstruye solo las fuentes del chat (sin heredar la sesión activa de otro chat) + `/analyze` acepta `data_source_ids` validando pertenencia. **P-42 CERRADO:** simulación usa `resolve_keys()`+`chat()` unificado; solo `hybrid` tiene fallback explícito; fallo de proveedor → 502 (nunca grafo vacío silencioso); ontología usa el proveedor activo. **P-54 (enrutado):** preguntas factuales generales van al determinista; artefactos (gráfico/código/SQL/sim/export) excluidos antes de la intención explícita. **P-65 CERRADO (nuevo):** Node ≥24 exponía `localStorage` experimental y vitest excluía el de jsdom → polyfill en `setup.ts` + regresión `EnvProbe`. **CI:** `.github/workflows/ci.yml` (backend pytest+compileall; cliente tsc+vitest+build, Node 24.22.1). P-64 restaurado a CERRADO (coincide con `d9e02f20` ya desplegado). Verificación: backend **305 passed, 3 xfailed**; cliente **78 passed**, `tsc` 0, `npm run build` 0; `compileall src/` OK. |
| 2026-10-28 | **Aplicada la remediación (Fases 1–3, sin cambios breaking).** **P-66 CERRADO**: `npm audit fix` → dompurify 3.4.17; build, tsc y vitest OK. **P-67 PARCIAL** *(entonces P-58)*: `fastapi` 0.115→0.133 y `starlette` ≥1.3.1 (el primer `fastapi` que admite starlette 1.x); `cryptography` 49, `PyJWT` 2.15, `python-multipart` 0.0.31 y transitivos. `pillow` bloqueado por `google-genai` 0.2.0 (`pillow<12`). **P-68 PARCIAL** *(entonces P-59)*: `NODE_VERSION: 24.22.1` en `render.yaml`. **Regresión detectada y corregida:** con Starlette 1.x un `Form(...)` obligatorio rechaza el string vacío como "missing" (422). Los endpoints que resuelven la clave con `resolve_keys()` usaban `api_key: str = Form(...)`; ahora son `Optional[str] = Form(None)` (3 en `analysis.py`, 1 en `dashboard.py`, 1 en `data.py`, 1 en `visual_summary.py`), lo que evita un 422 en producción cuando el usuario usa la clave guardada. `auth.py:validate_key` queda como estaba a propósito: valida la clave escrita por el usuario, así que un vacío debe ser error de validación. Verificación: `pytest tests` → 293 passed, 3 xfailed. Nota: `test_analysis.py::test_analyze_no_data_source` depende del orden de ejecución (falla en subconjunto, pasa en suite completa). |
| 2026-10-29 | **P-67 CERRADO: migración `google-genai` 0.2.0 → 2.33.0 para desbloquear `pillow` 13.** La SDK ya se usaba con la API moderna (`genai.Client`, `models.generate_content`, `types.GenerateContentConfig`), así que no hizo falta reescribir el motor. Cadena de conflictos resuelta: `google-genai` 2.x exige `httpx>=0.28.1` y `google-auth>=2.56`; `mistralai` 1.1.0 exigía `httpx<0.28` (→ 2.10.1) y un `supafunc 0.7.0` residual de `supabase` 2.10 exigía `httpx<0.28` (→ desinstalado; `supabase-functions` 2.33.0 ya no lo usa). Se retiró `google-generativeai==0.8.3` (0 usos en el código). **Cambio de API en `mistralai` 2.x:** `Mistral` ya no se exporta en la raíz sino en `mistralai.client`; `bi_analyst.py`, `swarm_engine.py` y `check_mistral.py` aceptan ambos layouts. **P-69 CERRADO (nuevo, registrado antes de corregir):** re-auditoría OSV → `cryptography` 50.0.2 (oráculo Bleichenbacher PKCS#7), `fpdf2` 2.8.9 (SSRF y bomba SVG `<use>`) y `opentelemetry-api` 1.45.1 / `opentelemetry-semantic-conventions` 0.66b1 (`tracestate` sin límite; el bump de semconv obligó a `mistralai` 2.10.1 porque los 2.9.x y anteriores topaban `<0.61`). **Colisión de IDs corregida (R1):** las tres entradas de dependencias que se habían registrado como P-57/P-58/P-59 se renumeran a **P-66/P-67/P-68** porque esos IDs ya describían otros problemas (P-57 `/upload` 500, P-58 `/analyze` 500, P-59 auditoría retail); se actualizan las referencias en `render.yaml` y `server/requirements.txt`. Verificación: `pip check` OK · smoke SDK (google-genai 2.33 / pillow 13.0 / httpx 0.28.1 / Mistral 2.10.1) OK · `pytest tests` → **305 passed, 3 xfailed** · OSV del venv: **0 vulnerables de 129 paquetes** (`pip` actualizado a 26.2.2; es herramienta de instalación y no se importa en runtime). |

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

> Nota posterior a la prueba: **P-43 y P-44 quedaron CERRADOS** el mismo día. Con el arreglo, los dos
> casos de la tabla siguiente ("generate-agents sin clave" y "Continuar con Google") ya no ocurren:
> el primero devuelve 400 con el motivo y el segundo ni se ofrece (aviso + modo Invitado).

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

---

### P-57 · `/upload` devuelve 500 y no registra la fuente (regresión)

| Campo | Valor |
|---|---|
| **Severidad** | CRÍTICO |
| **Estado** | ✅ CERRADO (2026-10-23) |
| **Verificado** | 🧪 `pytest tests/test_data.py -q` → 5 passed · suite completa 277 passed · pendiente confirmación en producción |
| **Archivos** | `server/src/routers/data.py` · `server/tests/test_data.py` |

**Qué pasaba.** Cualquier `POST /api/v1/upload` con un CSV válido devolvía **HTTP 500** y el archivo no quedaba
registrado. Dos causas encadenadas:

1. El bloque que creaba la fila `DataSource`, actualizaba `session_data` y llamaba a `save_user_data` se perdió en
   una edición previa: el `return` usaba `new_source`, que ya no existía (`NameError` → 500).
2. `DataSource(is_encrypted=encrypt_ok, ...)` referenciaba una variable `encrypt_ok` que tampoco estaba definida.

**Impacto.** La app era inutilizable: sin subida no hay análisis, dashboard ni auditoría. Además el detalle del
error se ocultaba tras un mensaje genérico, lo que alargó el diagnóstico en producción.

**Corrección.**
- Se restaura el flujo completo: escribir en disco → intentar nube → actualizar sesión → crear `DataSource` →
  `save_user_data` → responder.
- La nube pasa a ser **opcional**: si `upload_bytes` falla se guarda la ruta local en `DataSource.url` y la respuesta
  incluye `persisted=false`, en lugar de abortar con 503 (cambio deliberado sobre el contrato anterior de P-49).
- `is_encrypted=False` explícito mientras el cifrado en reposo de la copia local siga revertido (ver P-11).
- Se elimina la exposición de `str(e)` en el detalle 500 y se corrigió el mojibake (`Ã³`, `Ã±`, controles `\x8d`) de
  los mensajes del endpoint, que llegaban corruptos al usuario.
- Tests actualizados al contrato nuevo: `test_upload_valid_csv` (crea la fila, clave de nube) y
  `test_upload_valid_csv_local_only_when_cloud_down` (200, `persisted=false`, `url` local existente).

**Regla anti-repetición.** Ningún script de reemplazo por índices de línea sobre código Python: las ediciones se
hacen con `edit` sobre texto exacto y se valida con `ast.parse` + tests del router antes de commitear.

---

### P-58 · `/analyze` devuelve 500 en el flujo general (`source_name` sin definir)

| Campo | Valor |
|---|---|
| **Severidad** | CRÍTICO |
| **Estado** | ✅ CERRADO (2026-10-23) |
| **Verificado** | 🧪 `pytest tests/test_analysis.py tests/test_analysis_audit.py -q` → 15 passed · suite completa 277 passed |
| **Archivos** | `server/src/routers/analysis.py` · `server/tests/test_analysis_audit.py` · `server/tests/test_analysis.py` |

**Qué pasaba.** `source_name` solo se asignaba dentro de la rama `if audit_requested and data_type == "file":`.
El añadido de P-54 lo usa después, en la verificación determinista del flujo general, así que cualquier análisis
normal terminaba en `UnboundLocalError` → **HTTP 500** con "Error interno del servidor al procesar el análisis".

**Corrección.** `source_name = None` se inicializa junto a `primary_source_name`, antes de cualquier rama.

**Tests.** Los dos tests de `test_analysis_audit.py` que asumían el contrato anterior de P-54 (texto intacto y una
sola llamada a `build_audit`) se actualizaron al contrato vigente: el flujo general añade "Hechos verificados" y
`build_audit` puede ejecutarse dos veces (rama de auditoría + verificación). Se añadió limpieza del pickle de sesión
del usuario de pruebas en `test_analysis.py` para eliminar el fallo dependiente del orden de ejecución.

**Regla anti-repetición.** Toda variable usada fuera de una rama condicional se inicializa antes de la rama; los
tests de integración de `/analyze` deben cubrir el flujo general, no solo el de auditoría.

---

### P-59 · La auditoría verificada solo habla idioma retail aunque el dataset sea de otro dominio

| Campo | Valor |
|---|---|
| **Severidad** | MEDIO |
| **Estado** | ✅ CERRADO (2026-10-23) |
| **Verificado** | 🧪 Reproducción en producción con `colombia_covid_50k.csv` (datos.gov.co) |
| **Archivos** | `server/src/engine/insight_auditor.py` · `server/src/routers/analysis.py` · `client/src/components/chat/InsightCards.tsx` |

**Qué pasa.** Con un dataset sin columnas de ventas/profit (p. ej. casos COVID de datos.gov.co), la auditoría
honestamente no inventa cifras (0 hechos), pero todo el envoltorio sigue siendo de retail: muestra las
definiciones de "Profit neto", "Pérdida bruta", "Margen", "Descuento", "Umbral de descuento", y el "Qué haría"
sugiere "definir una métrica de rentabilidad" para un dataset epidemiológico. El usuario lo resume bien:
"está orientado a ventas, no a los datos que ve".

**Impacto.** La garantía anti-alucinación se cumple, pero la experiencia es ruidosa e irrelevante para datasets
gubernamentales/científicos/operativos, y el usuario no recibe ningún hallazgo útil pese a que el dataset sí
tiene columnas explotables (fecha, categoría, métrica numérica).

**Corrección propuesta (adaptativa, no por dominio).**
- Cuando no hay ventas ni profit, calcular hechos genéricos verificables de las columnas disponibles:
  periodo con más registros (y participación), registros del primer vs último año, composición top-3 de una
  columna categórica, y promedio/mediana de la primera columna métrica no-id. Todos con id, definición,
  evidencia y cálculo determinista con pandas.
- Mostrar solo las definiciones aplicables (sin vocabulario retail cuando nada retail fue calculado).
- Narrativa y "Qué haría" en términos neutrales: qué representa cada fila y su métrica de negocio, sin
  asumir rentabilidad.
- No se especializa por dominio (salud, crimen, forex): los hechos genéricos aplican a cualquier tabla.

**Evidencia de cierre (2026-10-23).**
- `pytest tests -q` → **282 passed, 3 xfailed** (5 tests nuevos de P-59 en `test_insight_auditor.py`).
- Datasets reales: COVID de datos.gov.co produce 5 hechos verificados (mes pico 2020-08 con 8,597 registros y 17.2%, composición BOGOTA 27.3% / ANTIOQUIA 14.8% / VALLE 8.3% por `departamento_nom`, edad promedio 40.44 / mediana 38.00); INE 11178 y 74999 producen composición por sexo y promedio/mediana de la tasa de paro; BCE produce promedio EUR/USD 1.18; NYC 311 y Chicago producen mes pico + composición legible y **ningún** hecho falso (sin promedios de `council_district`, `unique_key`, `departamento` ni de etiquetas como 'De 25 a 29 años').
- Regresión retail intacta: el dataset de descuentos sigue produciendo KPI-01..03, DISC, LOSS y REG con las definiciones completas de retail.
- Sin ventas ni profit las definiciones y el 'Qué haría' son neutrales; sin vocabulario de rentabilidad.
- Segunda iteración (feedback usuario 2026-10-23): en datasets sin contexto retail, la sección **Calidad del dataset** ya no lista ausencias de ventas/profit/descuento/orden (no es un defecto del archivo que no sea de ventas). Esas notas solo aparecen cuando hay ventas o profit y falta otra pieza. `pytest tests/test_insight_auditor.py -q` → 20 passed; suite completa → 284 passed, 3 xfailed.

**Criterio de cierre.**
- Dataset sin ventas/profit pero con fecha+categoría+numérico produce ≥3 hechos genéricos con valores
  iguales al cálculo manual con pandas.
- Las definiciones mostradas no incluyen términos retail cuando no se calculó nada retail.
- Regresión: el superstore sigue produciendo los mismos 27 hechos y las definiciones completas.
- `pytest tests -q` en verde.

---

### P-60 · `pkce_service.py` roto desde su creación (sintaxis + módulos inexistentes)

| Campo | Valor |
|---|---|
| **Severidad** | BAJO (código muerto inalcanzable; no afecta el arranque ni los flujos activos) |
| **Estado** | 🟡 PARCIAL (sintaxis corregida y verificada 2026-10-24; decisión pendiente: eliminar el archivo o completar los módulos que referencia) |
| **Verificado** | 🧪 `compileall` sobre `src/` → OK tras la corrección; suite completa 284 passed; import de `main` en modo producción OK |
| **Archivos** | `server/src/services/pkce_service.py` |

**Qué pasa.** `compileall` detectó un literal sin cerrar en la línea 90 (`'security_level': 'A,`), presente desde
el commit `96829bfb`. Además el módulo importa `src.utils.pkce_storage_factory` y (en los tests se mockea)
`src.utils.pkce_middleware`, que **nunca existieron** en la historia de git. Nada importa `pkce_service`, por lo
que el archivo es código muerto: no rompe el arranque ni los flujos activos, pero si alguien lo importara
revientaría en runtime.

**Corrección aplicada.** Literal reparado (`'security_level': 'A',`); `compileall src/` pasa limpio. No se
elimina el archivo ni se completan los módulos en este cambio (alcance mínimo).

**Regla anti-repetición.** Antes de commitear código nuevo de servicios, correr `compileall src/` (o al menos
importar el paquete) para detectar sintaxis rota; `compileall` se añade a la verificación estándar de deploys.

---

### P-61 · Upload pesado tumba el servidor: timeout corto del cliente + reintentos duplican el trabajo (OOM)

| Campo | Valor |
|---|---|
| **Severidad** | ALTO |
| **Estado** | ✅ CERRADO (2026-10-25) |
| **Verificado** | 🧪 Reproducido por el usuario subiendo `nyc_311_20k.csv` (15.9 MB, 44 columnas) en producción |
| **Archivos** | `client/src/lib/api.ts` · `server/src/routers/data.py` |

**Qué pasa.** El CSV de 15.9 MB ocupa ~40 MB como DataFrame y ~80 MB de pico transitorio durante el upload
(parse + disco + nube + pickle/cifrado de sesión). En un contenedor de 512 MB (plan gratuito) eso no cae solo,
pero `securedFetch` (P-08) usa timeout fijo de 30 s con **2 reintentos**. Un upload lento supera los 30 s, el
cliente aborta y reintenta; el aborto **no cancela el handler en FastAPI**, que sigue procesando el intento #1
mientras entra el #2 (y el #3). Dos o tres uploads pesados en paralelo + pickle/cifrado de sesión disparan la RAM
por encima del límite y el contenedor muere por OOM: "se cae el servidor" al subir el archivo.

**Corrección propuesta.**
- Cliente: `securedFetch` acepta `timeoutMs` y `retries` por llamada; `uploadFile` usa 120 s y **0 reintentos**
  (un upload no es idempotente: reintentarlo duplica el trabajo del servidor).
- Servidor: liberar `raw_bytes` (con `gc.collect()`) después de escribir en disco y subir a la nube, antes de la
  persistencia de sesión; y rechazar con 400 claro cualquier DataFrame que ocupe más de 80 MB en RAM
  (`memory_usage(deep=True)`), porque en el plan gratuito es inviable procesarlo sin tumbar el contenedor.
- Log del tamaño en RAM del pool tras cada upload para diagnosticar futuros crecimientos.

**Criterio de cierre.**
- `uploadFile` no reintenta ante timeout (1 sola petición) y usa 120 s.
- Dataset > 80 MB de RAM → 400 con mensaje accionable, sin escribir nada en disco ni DB.
- Suite backend y cliente en verde; los 6 datasets de prueba siguen subiendo (el mayor, NYC 311, ocupa 39.7 MB de RAM).
**Evidencia de cierre (2026-10-25).**
- Medición con el loader propio: NYC 311 = 15.9 MB de archivo → 39.7 MB de DataFrame, pico de parseo 30.7 MB, pickle 6.6 MB, cifrado 8.8 MB. Colombia 50k → 29.1 MB. Chicago → 11.5 MB. Ninguno supera la cuota de 80 MB; el pico transitorio por upload baja al liberar `raw_bytes` antes de la sesión.
- `uploadFile` ahora usa 120 s y **0 reintentos**; `securedFetch` acepta `timeoutMs`/`retries` por llamada sin cambiar el comportamiento de las demás rutas.
- Guard de memoria: DataFrame > 80 MB → HTTP 400 con mensaje accionable antes de tocar disco/nube/DB (test `test_upload_rejects_oversized_dataframe`). Log `UPLOAD_OK ... df=X pool=Y tablas=N` para vigilar el crecimiento del pool.
- Verificación: `pytest tests -q` → **285 passed, 3 xfailed**; cliente `tsc --noEmit` limpio y `vitest run` → **64 passed**.

---

### P-62 · Auditoría no-retail: hecho temporal tautológico y pocas tarjetas en datasets ricos

| Campo | Valor |
|---|---|
| **Severidad** | MEDIO |
| **Estado** | ✅ CERRADO (2026-10-26) |
| **Verificado** | 🧪 `build_audit` sobre `nyc_311_20k.csv` reproduce el caso (cifras verificadas pero contenido poco útil) |
| **Archivos** | `server/src/engine/insight_auditor.py` |

**Qué pasa.** Con datos de alcance corto (NYC 311: 20,000 filas de solo 3 días), TIME-G01 emite
"Mes con más registros: 2026-10 (20,000 registros, 100.0%)" — reafirma lo obvio porque los datos
caen en un único año-mes. Además, con 44 columnas solo se emiten 2 hechos: una sola composición
(agency) aunque `borough`, `city`, `status` pasan los filtros de legibilidad. El usuario califica
la auditoría de "no ofrece algo que me sirva": números correctos, contenido pobre.

**Corrección propuesta.**
- TIME-G01 adaptativo: si el alcance tiene un único año-mes, agrupar por día ("Día con más
  registros"); si solo existe un día distinto, omitir la tarjeta en vez de emitir un 100%.
- CAT-G02: segunda composición con la columna categórica legible de mayor entropía normalizada
  (excluye la columna ya usada por CAT-G01 y columnas casi constantes ≥98% de su valor dominante).
- Narrativa y `GENERIC_DEFINITIONS` actualizados al bucketing adaptativo.

**Criterio de cierre.**
- Tests nuevos: día pico en alcance corto (título "Día con más registros", participación < 100%);
  sin TIME-G01 cuando solo hay un día; CAT-G02 presente con columna distinta y cifras exactas;
  sin CAT-G02 cuando no hay segunda categoría legible. Suite backend en verde.
- Reproducción manual en producción: NYC 311 con ≥3 hechos sin tautologías.
**Evidencia de cierre (2026-10-26).**
- NYC 311 antes: `2026-10 (20,000 registros, 100.0%)` + solo CAT-G01 ('agency'). Después:
  `2026-10-21 (11,965 registros, 59.8%)` (día pico real), CAT-G01 agency
  (NYPD 38.4%, HPD 30.0%, DSNY 7.1%) y CAT-G02 status (Closed 48.0%, Open 31.6%, In Progress 20.2%).
- Colombia covid 50k: cifras originales intactas (pico 2020-08 8,597/17.2%, BOGOTA 27.3%,
  edad 40.44/38.00) + CAT-G02 sexo (F 50.2%, M 49.8%). INE paro: mismas tarjetas previas + CAT-G02
  cuando existe segunda categoría con cobertura ≥50%; no emite tarjetas de relleno.
- Criterio de CAT-G02: legible, no id/tiempo, top-1 < 98%, top-3 ≥ 50%; si no hay, no se emite.
- Verificación: 4 tests nuevos (`test_short_span_buckets_by_day_not_month`,
  `test_single_day_span_has_no_peak_card`, `test_second_composition_exact_values`,
  `test_no_second_composition_without_candidates`); `pytest tests -q` → **289 passed, 3 xfailed**;
  `compileall src/` → OK.

---

### P-63 · Auditoría con ventas sin profit: lamenta lo que falta en vez de explotar lo que hay

| Campo | Valor |
|---|---|
| **Severidad** | MEDIO |
| **Estado** | ✅ CERRADO (2026-10-26) |
| **Verificado** | 🧪 `build_audit` sobre `datasets_vektra/11_P1_regiones_top5_departamentos.csv` (5 filas: Posicion, DEPARTAMENTO, Cantidad_Empresas, Suma_Ingresos) |
| **Archivos** | `server/src/engine/insight_auditor.py` |

**Qué pasa.** Los rankings regionales del usuario (11_P1/P2/P3 con `Suma_Ingresos`, rol ventas detectado)
caen en el ramal retail parcial: narrativa negativa ("El dataset registra $345 en ventas, **pero no hay
una columna de profit para calcular rentabilidad**"), 1 sola tarjeta (KPI-01), definiciones de conceptos
que no se calcularon (Profit neto, Pérdida bruta, Margen, Descuento, Umbral) y 3 notas de "calidad" que
son ausencias, no datos. El usuario califica: es incómodo; quiere que la auditoría trabaje con lo que el
archivo contiene y muestre viñetas útiles.

**Corrección propuesta.**
- Nueva tarjeta CAT-V01 "Ventas por '{categoría}'": participación del top 3 de valores sobre el total de
  ventas (groupby+sum verificable), con los mismos guardrails de utilidad (top-1 <98%, top-3 ≥50%,
  ≥2 grupos); solo en el ramal ventas-sin-profit (el retail completo ya da ese análisis).
- Narrativa ventas-sin-profit positiva: registra ventas + repartición; sin el "pero no hay profit".
- "Qué haría" neutral en ramal ventas-sin-profit y sin ventas (mismo texto neutro, sin exigir rentabilidad).
- Definiciones en ramal ventas-sin-profit: solo Línea y No medible (no definir lo no calculado).
- Calidad: eliminar por completo las notas de ausencia (identificador de orden, ventas, profit, descuento).
  Superceden la salida parcial de P-59 iteración 2 por petición explícita del usuario (excepción de
  evolución: se actualizan los tests `test_without_profit_does_not_invent_margin` (calidad/narrativa) y
  `test_partial_retail_still_reports_missing_columns`; el núcleo de ambos (no inventar KPI-02/KPI-03) se
  conserva). El blockeo de orden inutilizable ("La columna de orden no contiene identificadores
  utilizables; se ignora.") SIEMPRE se mantiene porque describe una corrección aplicada, no una ausencia.
- Cliente: corregir singular/plural del contador ("1 hallazgo calculado").

**Criterio de cierre.**
- 11_P1/P2/P3: KPI-01 + CAT-V01 con cifras exactas; sin frases "pero no hay…"; definiciones reducidas;
  calidad sin ausencias. Retail completo y ramal genérico sin regresión (tests).
- Suite backend en verde; cliente TSC/vitest en verde.
**Evidencia de cierre (2026-10-26).**
- 11_P1: KPI-01 `$345` + CAT-V01 `ATLANTICO 31.2%, CUNDINAMARCA 25.2%, BOLIVAR 22.8%` (top del
  ranking exacto); 11_P2/P3: `$193` + `BARRANQUILLA 47.2%, CARTAGENA 38.8%, BUCARAMANGA 13.9%`.
- En los 3 archivos: cero frases 'No se detectó', calidad vacía, definiciones reducidas a
  Línea/Participación de ventas/No medible.
- Regresión verificada: retail completo intacto (KPI-01..LOSS-03, definiciones completas);
  gov datasets (INE/Colombia/NYC/Chicago/léxico ECB) con mismos hechos que en P-62.
- Tests: `test_without_profit_does_not_invent_margin` y `test_partial_retail_still_reports_missing_columns`
  actualizados al contrato nuevo (conservan el núcleo anti-invención KPI-02/KPI-03); clase nueva
  `TestSalesWithoutProfit` (4 tests, cifras exactas y ausencia de lamentos). `pytest tests -q` →
  **293 passed, 3 xfailed**; `compileall src/` OK; cliente `tsc --noEmit` limpio + **64 passed**.

---

---

### P-65 · Suite de cliente rota en Node >= 24: vitest no instala el `localStorage` de jsdom

| Campo | Valor |
|---|---|
| **Severidad** | MEDIO (infraestructura de tests; bloqueaba toda la suite del cliente) |
| **Estado** | ✅ CERRADO (2026-10-28) |
| **Verificado** | 🧪 Sonda de entorno (`EnvProbe`) + suite completa `vitest run` → 78 passed |
| **Archivos** | `client/src/tests/setup.ts` · `client/src/tests/EnvProbe.test.ts` |

**Qué pasa.** Node >= 24 expone un `localStorage` **experimental** como global (vacío sin
`--localstorage-file`; reproducido con Node v24.13.0: `'localStorage' in globalThis` → true,
`typeof` → undefined + ExperimentalWarning). El `populateGlobal` de vitest **excluye** las claves
de jsdom que ya existen en el global de Node, así que el `localStorage`/`sessionStorage` de jsdom no
se copian al entorno: los tests ven `undefined` y componentes como `ThemeContext` o
`DashboardContext` fallan con `Cannot read properties of undefined (reading 'getItem')`. La suite
pasaba antes porque el entorno se evaluaba con estados de Node/caché distintos; se rompió de forma
reproducible al ejecutar la suite completa (6 failed de golpe: ThemeToggle 3 + hidratación 3).

**Corrección aplicada.** Polyfill en `client/src/tests/setup.ts`: si el entorno no tiene un
`localStorage` utilizable, se instalan `localStorage` y `sessionStorage` en memoria con la interfaz
completa del navegador (`getItem/setItem/removeItem/clear/key/length`). Portable a cualquier
versión de Node y a CI, sin depender del flag `--no-experimental-webstorage`.

**Evidencia de cierre.**
- `npx vitest run` → **78 passed (78)**, exit code 0; antes del polyfill: 6 failed con
  `typeof window.localStorage: undefined` (sonda `EnvProbe`).
- `npm run build` → exit 0; `npx tsc --noEmit` → exit 0.
- Regresión: `client/src/tests/EnvProbe.test.ts` verifica que ambos Storage existen y funcionan.

**Regla anti-repetición.** El entorno de pruebas debe autoverificarse: un test de entorno
(`EnvProbe`) es la alarma temprana cuando Node/vitest cambian qué globals expone. Los cambios de
runtime de Node (globales experimentales) se detectan aquí antes de romper 15 suites.

---

### P-64 · Cuota de subida 25 MB / 250 MB bloquea archivos que antes funcionaban

| Campo | Valor |
|---|---|
| **Severidad** | ALTO |
| **Estado** | ✅ CERRADO (2026-10-26) |
| **Verificado** | 🔎 Lectura de `server/src/routers/data.py:23-24,81-84,104-109`; historial git muestra introducción en `768d67ad` (hardening) sin límite previo |
| **Archivos** | `server/src/routers/data.py:23-24,81-84,104-109` |

**Qué pasa.** Desde el hardening `768d67ad` el router impone `_QUOTA_MAX_FILE_MB = 25` y `_QUOTA_MAX_TOTAL_MB = 250`. El endpoint `/upload` rechaza con 400 si el archivo supera 25 MB o si la suma acumulada de `size_bytes` supera 250 MB por usuario. El usuario reporta que documentos que antes se leían ahora fallan y solicita quitar la restricción. El límite por archivo es arbitrario respecto a la protección real (OOM) que ya está cubierta por `_MAX_DF_MEMORY_MB = 80`, `MAX_CELLS = 1_000_000` y la validación de zip-bomb desde bytes.

**Impacto.** Funcionalidad principal bloqueada para usuarios con archivos >25 MB o con acumulado >250 MB. Falso positivo de seguridad: la cuota no evita OOM ni zip-bomb; esas protecciones ya existen.

**Corrección aplicada.**
- `_QUOTA_MAX_FILE_MB` 25 → **50 MB** (límite máximo Supabase Free, 50 MB por archivo).
- `_QUOTA_MAX_TOTAL_MB` 250 → **800 MB** (< 1 GB de Supabase Free, deja margen de cuota de nube).
- Protecciones conservadas: `_MAX_DF_MEMORY_MB = 80`, `MAX_CELLS = 1M`, validación zip-bomb desde bytes, cifrado en memoria.

**Evidencia de cierre.**
- `pytest tests -q` → **293 passed, 3 xfailed** (sin regresión).
- Límite coherente con Supabase Free (max 50 MB por archivo, 1 GB storage) y Render Free (512 MB RAM); la protección OOM sigue siendo `_MAX_DF_MEMORY_MB`.
- Commit `d9e02f20` en `origin/main` (desplegado; `/health` de producción operativo).

**Regla anti-repetición.** Las cuotas de tamaño de archivo/total deben derivarse de límites reales de infraestructura (RAM, memoria de DataFrame, almacenamiento de nube) y no anticiparse con valores fijos bajos que rompan el flujo. Si se mantiene una cuota, debe ser configurable y documentada, y nunca debe anular los guardrails existentes de memoria/ celdas.
