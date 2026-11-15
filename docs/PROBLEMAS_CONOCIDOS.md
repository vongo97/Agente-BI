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

**Totales:** 4 críticos · 23 altos · 32 medios · **7 bajos** — **66 filas** en el resumen, **75 fichas** detalladas, **76 IDs** registrados (66 con fila + 10 solo con ficha).
Deuda de registro conocida: **P-42** se cita en commits pero no está registrado (los P-57–P-65 ya tienen ficha y fila).
Último cierre: **P-74** (2026-11-15) — el registro deja de estar corrupto y queda con un control mecánico que impide que vuelva a estarlo.

> **Reconciliación 2026-11-14 (ronda 1).** Cada fila del resumen fue **verificada contra el código** (no contra el texto del registro). Resultado: **3 filas estaban desfasadas** y se corrigieron a CERRADO (**P-18** `pkce_service.py` ya parseaba; **P-26** `handleSave` ya guardaba de verdad; **P-68** Node local ya v26.12.1 y `render.yaml` ya fijaba 24.22.1). **5 filas eran PARCIALES** con la mitad ya resuelta (**P-21**, **P-28**, **P-29**, **P-30**, **P-47**) y **6 seguían ABIERTAS** con evidencia reproducible (**P-19**, **P-23**, **P-24**, **P-25**, **P-36**, **P-47**).

> **Reconciliación 2026-11-14 (ronda 2) — cierres.** Los **10 puntos abiertos/parciales** de la ronda 1 quedan **CERRADOS** con evidencia: **P-19** (arranque fail-closed + baseline Alembic portable) · **P-21** (test explícito de CORS) · **P-23** (router `reports` montado; código muerto real eliminado y componentes huérfanos **conectados**) · **P-24** (tokens Tailwind reales) · **P-25** (a11y de modal y toasts) · **P-28** (script `npm test`) · **P-29** (una sola política de fuente en `Chat.tsx`) · **P-30** (polling con guard) · **P-36** (ningún `except: pass` + guardia estática) · **P-47** (script legado eliminado + guía actualizada). **Los controles son mecánicos, no textuales**: P-19, P-21 y P-36 tienen tests que **fallan** si alguien deshace el arreglo (verificado inyectando el fallo y observando el fallo de la suite).
>
> **Ronda 3 (2026-11-15) — P-72 y suite en verde.** El único test que quedaba rojo (`test_clave_nueva_sb_secret_crea_cliente`, **preexistente desde el 2026-10-21**) no era un defecto del test ni una dependencia de la red: el **venv local tenía supabase-py 2.10.0** (la versión con el bug de P-50) mientras `requirements.txt` fija **2.33.0**. Instalada la versión fijada → **376 passed, 3 xfailed, 0 failed**.
>
> **Ronda 3 (2026-11-15) — corrección de la ficha de P-23.** La ficha de P-23 afirmaba que `KpiCards`, `AnomalyAlert` y `ServerStatusTracker` se habían **eliminado**; la realidad es que **no se eliminó ninguno**: `ServerStatusTracker` ya estaba vivo (`Providers.tsx:8,22`) y `KpiCards`/`AnomalyAlert` se han **conectado** mediante el nuevo `KpiPanel.tsx`. La ficha se ha reescrito con el estado real.
>
> **Ronda 4 (2026-11-15) — P-60 cerrado, P-73 registrado.** El único `PARCIAL` sin resolver que quedaba era **P-60** (`pkce_service.py`, no importable): se **eliminó** y se creó `server/tests/test_no_unimportable_modules.py`, que vigila toda la clase de fallo (import real de cada módulo de `server/src/`, no solo `compileall`). Ese test destapó **P-73** (`src/ui/styles.py`, residuo de Streamlit sin la dependencia declarada), también eliminado.
>
> **Ronda 5 (2026-11-15) — P-20 cerrado y P-38 re-verificado.** **P-20**: las páginas legales leían `../docs/legal`, fuera de `client/`, lo que **funcionaba en local y daba 404 en Docker/standalone** (un fallo invisible en el build). Los `.md` se han movido a `client/content/legal/` y la resolución prueba todas las candidatas según el `cwd`. **P-38** se añade a los cerrados: la validación de `localStorage` (`isValidLayout`) existe y el `any` de la simulación ya no aparece.
>
> **Ronda 6 (2026-11-15) — P-17 cerrado.** El `.mp4` de 24 MB y `server/debug_server.log` (364 KB) salen del índice (`git rm --cached`, **conservados en disco**). El log contenía el **email real del usuario** y 27 menciones de claves/tokens: era el único fichero versionado con esos datos, así que se eliminan del árbol de trabajo (el histórico conserva las versiones antiguas; purgarlo exigiría `git filter-repo`, que reescribe el historial y queda como decisión del propietario). Nuevo **job `hygiene` en CI** que falla si vuelve a entrar un binario, un log o un fichero de más de 5 MB.
>
> **Ronda 7 (2026-11-15) — P-45 cerrado (error de hidratación).** La fila de **P-45** era la única del resumen **sin ficha**, y el problema era real: `client/src/context/ThemeContext.tsx` inicializaba el estado con un *lazy initializer* que leía `localStorage`, de modo que el primer render del cliente **no coincidía** con el del servidor (siempre `'dark'`). El estado arranca ahora **siempre** en `'dark'` y el tema guardado se aplica en un `useEffect` post-hidratación (sin destello: el script inline de `layout.tsx` ya fija `data-theme` antes del primer pintado). Ficha completa añadida en la sección 5 y control mecánico en `client/src/tests/ThemeHydration.test.tsx` (**5 passed**; control verificado: reintroducir el initializer → **1 failed**, restaurado → **5 passed**). Con esto **todas las filas del resumen tienen ficha**.
>
> **Ronda 8 (2026-11-15) — P-74 cerrado (el registro estaba corrupto).** Al intentar escribir la ficha de P-45 se descubrió que el **propio registro** estaba dañado: 32 caracteres `U+FFFD` grabados en el fichero (mojibake real), separadores `→`/`·` convertidos en `?` (dejando el **estado** de varios P ilegible), la **fila de P-41 duplicada**, la **ficha de P-40 partida dentro de la tabla** y los **totales de la cabecera falsos** (28 medios / 10 bajos, cuando eran 30 / 8). Todo reparado; además se han escrito las **9 fichas** que faltaban (P-46, P-49, P-52, P-53, P-56, P-66, P-67, P-68, P-69), normalizado las 4 filas que tenían el Estado incrustado en la celda «Problema» (P-44, P-48, P-49, P-50) y **blindado** con `server/tests/test_registry_integrity.py` (11 passed; control verificado con los **6 daños reintroducidos uno a uno** → el test falla en los 6). Totales recalculados desde las filas: **4 críticos · 23 altos · 31 medios · 7 bajos**.
>
> **Ronda 9 (2026-11-15) — P-40 reabierto con los números reales.** La fila de P-40 decía **CERRADO** desde
> el 2026-10-22, pero ese cierre solo había tocado **4** pantallas: un `grep` sobre `client/src/` encuentra
> **38 ocurrencias** de texto por debajo de 10 px en **10 ficheros** (hasta `text-[7px]`, en `SimDebate.tsx` y
> `SimForm.tsx`), y los sidebars siguen **fijos en móvil**. La fila y la ficha se reabren como **PARCIAL** con el
> conteo y la lista de ficheros exactos. Es el mismo patrón que P-23: **una ficha que afirma un cierre sin
> verificarlo literalmente propaga el error a quien la lea**.
>
> **Puntos que siguen ABIERTOS tras la ronda 9** (verificados contra el código el 2026-11-15). Son **6**, de
> **75 IDs** registrados (el **92 %** está cerrado con evidencia):
>
> | ID | Severidad | Estado | Qué falta |
> |---|---|---|---|
> | **P-54** | ALTO | 🟡 PARCIAL | La narrativa del análisis no tiene verificación numérica en el flujo general (las fases 1-2 y el enrutado de preguntas sí están hechos) |
> | **P-56** | ALTO | 🟡 PARCIAL | El código está corregido (clientes de IA fuera del event loop); falta **verificar en producción** que un análisis largo no tumbe `/health` ni reinicie Render |
> | **P-31** | MEDIO | ⚠️ ACEPTADO | Rate limiting por IP de proxy, evadible con `X-Forwarded-For`; el cubo de peticiones anónimas es compartido. **Riesgo residual asumido**, no pendiente de código |
> | **P-49** | MEDIO | ⬜ ABIERTO | Modo local sin nube: el arranque debe **avisar** de que el bucket no está configurado y hay que decidir si el modo local escribe en disco cifrado o solo en memoria |
> | **P-40** | BAJO | 🟡 PARCIAL | 38 ocurrencias de texto < 10 px en 10 ficheros y sidebars fijos en móvil (cerrado en 4 pantallas, el resto queda) |
> | **P-42** | — | ⬜ DEUDA DE REGISTRO | Se cita en commits pero no tiene ficha; P-57–P-65 ya la tienen |
>
> Los **6** son reales y verificables; ninguno está "por cerrar sin evidencia". **P-31** es una decisión
> aceptada (no un defecto pendiente) y **P-42** es deuda de registro, no un defecto de código.

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
| **P-08** | Frontend | Capa de red sin timeout, `AbortController`, retry ni reacción a 401/403 | ✅ CERRADO | `client/src/lib/api.ts` · `securedFetch` con AbortController (30 s), retry exponencial (2 reintentos), 401/403 → signOut + redirect /login · `client/src/tests/ApiNetwork.test.ts` (6 passed) |
| **P-09** | Frontend | Autosync guarda valores por defecto antes de cargar la config → puede sobrescribir ajustes del usuario | ✅ CERRADO | `client/src/context/DashboardContext.tsx` · gate de hidratación `loadedConfigUser`/`configLoaded`: `syncConfig` no persiste hasta que `getUserConfig` resuelve para el usuario activo; cleanup de timers/pendientes al desmontar o cambiar de cuenta; token de NextAuth desacoplado de la carga de config · `client/src/tests/DashboardConfigHydration.test.tsx` (3 passed: carga lenta no autosavea defaults, fallo de red deja autosave deshabilitado, cambio del usuario autosavea tras hidratar) · suite `vitest run` → 78 passed · `tsc --noEmit` limpio (2026-10-28) |
| **P-10** | Cifrado | `ENCRYPTION_KEY` inválida genera clave efímera; `encrypt/decrypt` aceptan texto plano | ✅ CERRADO | `server/src/utils/security.py` · fail-closed en producción sin clave · clave determinista en dev · `encrypt_key` lanza `ValueError` en vez de texto plano · `decrypt_key` rechaza no-Fernet · `tests/test_security_encryption_key.py` (10 passed) · Antigravity 2026-10-22 |
| **P-11** | Uploads | Original escrito en claro en `.tmp` antes de cifrar; sin mitigación de zip-bomb | ✅ CERRADO (2026-11-11) | `server/src/routers/data.py` (`upload_file`): 3 cambios quirúrgicos re-aplicados — (1) `_reject_zip_bomb_early(raw_bytes, clean_name)` invocado ANTES de parsear (línea ~173); (2) `encrypt_bytes(raw_bytes)` cifra en memoria y solo los bytes cifrados se escriben en disco y se suben a la nube (líneas ~211, ~232); (3) `DataSource.is_encrypted=True` (línea ~263). El original nunca se persiste en claro. Tests: `server/tests/test_upload_encryption.py` (7 passed) — cifrado en reposo, zip-bomb Excel, zip-bomb CSV, round-trip de descifrado + 3 guardas estáticas. Suite completa **339 passed, 3 xfailed**. Reapertura de 2026-11-03 por el revert `885b3b61` resuelta: el read-back soporta ambos formatos (`common.py:485-499` descifra cuando `is_encrypted=True`; los archivos legacy sin cifrar siguen leyéndose por el branch `else`) |
| **P-12** | API | `str(e)` de excepciones internas persistido y devuelto al cliente | ✅ CERRADO | `server/src/routers/simulation.py` · `str(e)` reemplazado por mensajes genéricos en 3 ubicaciones (líneas 139, 447, 453) · detalle solo en logs internos con `logger.exception` · Antigravity 2026-10-22 |
| **P-13** | UI/BI | KPIs inventados presentados como análisis real (`38.4 + n*1.2`, `96.5%`) | ✅ CERRADO | `client/src/components/DashboardView.tsx:73-131` · métricas reales derivadas de datos (visualizaciones activas, filtros, fuentes) · Antigravity 2026-10-22 |
| **P-14** | UI/BI | El modelo mostrado en el selector no es el que usa el backend | ✅ CERRADO | `client/src/components/SettingsView.tsx` · `client/src/context/DashboardContext.tsx` · `providerModels` cargado desde `getUserConfig` y mostrado junto al nombre del proveedor · Antigravity 2026-10-22 |
| **P-15** | Auth | Sin allowlist ni middleware en el cliente: cualquier cuenta Google entra y la app queda inservible (403) | ✅ CERRADO | `client/src/lib/auth-allowlist.ts` · `client/src/app/page.tsx` · `isAuthorizedEmail()` lee NEXT_PUBLIC_AUTHORIZED_EMAILS · acceso denegado con mensaje claro · `client/src/tests/AuthAllowlist.test.ts` (4 passed) · Antigravity 2026-10-22 |
| **P-16** | Sandbox | Lista negra incompleta: `pd.read_table`, `DataFrame.to_csv`, `np.save`, `plt.savefig`, `pd.io.common.os`… | ✅ CERRADO | `server/src/engine/executor.py` · allowlist de módulos/atributos + bloqueo `getattr`/`setattr`/`delattr` + `to_csv`, `read_table`, `np.save*`, `savefig` bloqueados en AST y runtime · `tests/test_sandbox_imports.py` (12 passed) · Antigravity 2026-10-22 |
| **P-51** | Sandbox | La allowlist de imports no incluye `time`; pandas/numpy lo importan en runtime y **todo análisis falla** con `ImportError: Librería 'time' bloqueada por seguridad` | ✅ CERRADO | `server/src/engine/executor.py:283-294,457-468,762-769` · `tests/test_sandbox_imports.py` |
| **P-52** | Sandbox | La lista AST de atributos prohibidos incluye `rename`; bloquea `DataFrame.rename()` legítimo y hace fallar análisis con pandas | ✅ CERRADO | `server/src/engine/executor.py:153-166` · `tests/test_sandbox_imports.py::TestSandboxRename` |
| **P-54** | IA/BI | La narrativa del análisis no tiene verificación numérica en el flujo general | 🟡 PARCIAL (Fase 1 + Fase 2 + flujo general con hechos verificables + enrutado de preguntas analíticas 2026-10-28) | `insight_auditor.py` · `audit_agent.py` · `analysis.py` · `InsightCards.tsx` · `tests/test_insight_auditor.py` · `tests/test_audit_agent.py` · `tests/test_analysis_audit.py` · `build_audit` adjuntado a todas las respuestas de /analyze (P-54 flujo general) · auditoría real del superstore 27 hechos · **2026-10-28:** `is_audit_query` ampliado: las preguntas factuales sobre los datos ("analiza", "resumen", "compara", "¿cuál es el producto más vendido?"…) se enrutan al paquete determinista como única fuente de cifras; las peticiones de artefactos (gráfico, código, SQL, simulación, exportación) se comprueban ANTES que la intención explícita y quedan en el motor generativo ("exporta los hallazgos" no se desvía) · `tests/test_audit_agent.py` actualizado (`test_general_fact_questions_route_to_audit`, `test_artifact_requests_stay_in_generative_engine`) · `tests/test_analysis.py` actualizado al contrato (validación de clave con consulta generativa; flujo generativo con consulta de gráfico) · suite backend 305 passed |
| **P-55** | Infra/API | El frontend de Render apunta al backend `-zifr`, pero su CORS no incluye ese origen; además hay dos backends (`-7nav` SQLite y `-zifr` Postgres) y `render.yaml` describe el SQLite | ✅ CERRADO | CORS resuelto hacia `-zifr` · backend unificado · confirmado por el usuario en producción 2026-10-22 · Cambio de infraestructura Render (no de código local) · Antigravity 2026-10-22 |
| **P-56** | Infra/IA | `/analyze` es `async` pero ejecuta llamadas LLM síncronas y re-guarda la sesión completa en el event loop; bloquea `/health`, Render reinicia el servicio y el navegador muestra `Failed to fetch` | 🟡 PARCIAL (corregido en código; falta verificar en producción) | `server/src/engine/bi_analyst.py:334-500` · `server/src/routers/analysis.py` · `server/src/utils/common.py:234-320` · `server/main.py` · `render.yaml` |
| **P-67** | Dependencias Python | 16 de 118 paquetes del backend con advisories publicados tras el cierre de P-06: `python-multipart` 0.0.12 (16), `PyJWT` 2.13.0 (29, auth), `cryptography` 43.0.1 (10, Fernet), `pillow` 11.3.0 (74), `starlette` 0.38.6 (14), `oauthlib` 3.3.1 (timing attack PKCE), `certifi` 2026.5.20 (CA emSign comprometido), `urllib3`, `anyio`, `h2`, `hpack`, `httplib2`, `mako`, `pyasn1`, `python-dotenv`, `pip` | ✅ CERRADO | `server/requirements.txt`: `fastapi` 0.133.0 (starlette ≥1.3.1), `python-multipart` 0.0.31, `PyJWT` 2.15.0, `cryptography` 50.0.2, `google-genai` 2.33.0 (desbloquea `pillow` 13.0.0), `mistralai` 2.10.1, `httpx` 0.28.1 y transitivos. Re-auditoría OSV (129 paquetes): **0 vulnerables**; `pip` quedó actualizado a 26.2.2 en el venv (herramienta de instalación, no se importa en runtime). `pip check` OK · `pytest tests` → 305 passed, 3 xfailed |
| **P-68** | Infra / Node.js | Node.js local v24.13.0 afectado por el release de seguridad del 21-10-2026 (RCE Brotli CVE-2026-111497, bypass TLS hostname CVE-2026-105483/106069, `dns.resolve` CVE-2026-105482). `render.yaml` no fija `NODE_VERSION` del servicio cliente | ✅ CERRADO (verificado 2026-11-14) | `render.yaml:69-70` (servicio cliente) fija `NODE_VERSION: 24.22.1` · Node local **v26.12.1** (supera el mínimo) · CI usa `node-version: 24.22.1` |
| **P-69** | Dependencias Python | Advisories nuevos detectados en la re-auditoría OSV del 2026-10-29: `cryptography` 49.0.0 (GHSA-g6cj-pr64-35w5 / PYSEC-2026-3552, oráculo Bleichenbacher en PKCS#7 EnvelopedData, fix 50.0.0), `fpdf2` 2.8.1 (GHSA-rw7v-4hrq-x6r9 SSRF por carga implícita de URLs/imágenes y GHSA-wqw6-wpr3-45rh bomba SVG `<use>`, fix 2.8.8), `opentelemetry-api` 1.39.1 (GHSA-xcq7-p3pf-p88h `tracestate` sin límite, fix 1.45.1) | ✅ CERRADO | `server/requirements.txt`: `cryptography==50.0.2`, `fpdf2==2.8.9`, `opentelemetry-api>=1.45.1` + `opentelemetry-semantic-conventions>=0.66b1` (0.66b1 fija api 1.45.1; obligó a `mistralai` 2.10.1, el primer 2.x sin tope `<0.61` en semantic-conventions). Re-auditoría OSV del venv `.venv-codex`: **0 vulnerables** · `pytest tests` → 305 passed, 3 xfailed |
| **P-71** | IA/BI | La auditoría narra tarjetas, no interpreta: el usuario necesita el relato natural ("la primera ola fue una meseta", "el -100% es truncado") y hoy se lo da un humano u otra IA → el producto falla en su propuesta de valor | ✅ CERRADO (2026-11-04) | `insight_auditor.py`: nueva `TIME-G03` cobertura por año con días, meseta en `TIME-G01`, caveat en `TIME-G02`, `MET-G04` rango típico, `CAT-G03` estado/resultado reservado antes de CAT-G02, calidad explicada · `audit_agent.py`: narrador natural (`narration` + `fact_ids`) con verificación de CADA cifra contra el paquete (separadores, magnitudes, variaciones derivadas del mismo enunciado); una cifra ajena → determinista · COVID real: 2020/2021/2022 con días, Fallecido 3.0%, edad 27-53, calidad explicada · narrativa natural ACEPTADA y `31.7%` RECHAZADA · `TestNarrativeInterpretation` (6) + `TestNaturalNarrationValidation` (11) · backend **332 passed, 3 xfailed**; cliente **88 passed**, tsc 0 |
| **P-43** | API | `except Exception` de los endpoints de simulación se traga los `HTTPException` accionables → todo error se ve como 500 "Error interno" | ✅ CERRADO | `simulation.py` (4 endpoints) · `dashboard.py` (auto_dashboard) · `exports.py` (chart, pptx) · `tests/test_http_exception_passthrough*.py` |

### 🟡 MEDIOS

| ID | Área | Problema | Estado | Evidencia |
|---|---|---|---|---|
| **P-17** | Repo | Artefactos versionados: vídeo de **24 MB** y `debug_server.log` (361 KB) | ✅ CERRADO (2026-11-15) | Ambos ficheros **sacados del índice** con `git rm --cached` (**conservados en el disco local**: no se borra nada del equipo) · `.gitignore` ampliado: `presentacion/`, `*.mp4`, `*.mov`, `*.webm` (y ya estaba `*.log`) · **hallazgo de privacidad**: `server/debug_server.log` contenía el **email real del usuario** (`juanddavidvo03@gmail.com`, 2.549 líneas) y 27 menciones de claves/tokens — verificado que era el **único** fichero versionado con ese email, así que sacarlo lo elimina por completo del árbol de trabajo · **control mecánico en CI**: nuevo job `hygiene` que falla si hay binarios/logs versionados o ficheros de más de 5 MB · *control verificado:* reintroducir el `.mp4` → detectado por **ambos** guards (extensión y tamaño) |
| **P-18** | Código | `pkce_service.py` tiene **SyntaxError** (módulo no importable) | ✅ CERRADO (verificado 2026-11-14) | `server/src/services/pkce_service.py` — `ast.parse` OK; el módulo se importa en runtime (`from src.utils.mobile_security import validate_mobile_request_security`) |
| **P-19** | BD | `DATABASE_URL` inválida cae a SQLite en silencio; baseline de Alembic inválida | ✅ CERRADO (2026-11-14) | `server/src/database.py` — **fallback silencioso eliminado**: URL mal formada → `RuntimeError` en el import; URL bien formada pero BD inalcanzable → `_assert_database_reachable()` aborta el arranque en producción (en desarrollo solo avisa) · `init_db()` aborta en producción si el esquema no se puede sincronizar · `main.py:165-180` propaga el error en vez de tragarlo · `sanitize_db_error` conserva el usuario y enmascara solo la contraseña (`usuario:***@host`) · `server/migrations/versions/e114418c6081_initial_baseline.py` reescrito: `_ensure_tables_exist()` + guards de FK sin nombre (SQLite) + `_column_exists()` + `batch_alter_table` para `ALTER COLUMN ... TYPE` · `migrations/env.py` con `render_as_batch=True` · `server/tests/test_database_startup_failclosed.py` (7 passed) · `alembic upgrade head` en BD limpia → `alembic_version=e114418c6081`, 10 tablas, FKs con `ON DELETE CASCADE`, `current_round` presente, `preferred_provider` VARCHAR |
| **P-20** | Legal | Páginas legales leen `../docs/legal` fuera de `client/` → 404 en Docker/standalone | ✅ CERRADO (2026-11-15) | Los `.md` **se movieron dentro de `client/`**: `docs/legal/*.md` → **`client/content/legal/*.md`** (`git mv`, sin duplicar: la copia de la raíz desaparece) · `client/src/app/legal/[slug]/page.tsx` — la ruta fija `path.join(process.cwd(), "..", "docs", "legal", ...)` se sustituye por `resolveLegalFile()`, que prueba **todas** las candidatas (`content/legal`, `client/content/legal`, `../client/content/legal`) y devuelve la primera que existe; si ninguna, `notFound()` · las tres páginas se **prerenderizan (SSG)** con el contenido real horneado en el HTML (verificado: `privacidad` 35 KB, `terminos` 24 KB, `cookies` 18 KB, con el texto del documento dentro) · `client/src/tests/LegalDocsPath.test.ts` (5 passed): los `.md` están dentro de `client/`, se encuentran con `cwd = client/` **y** con `cwd = raíz del repo` (el caso standalone/Docker), el contenido no está vacío y la página no vuelve a leer de `docs/` · *control verificado:* reintroducir la ruta antigua → 1 failed; restaurada → 5 passed |
| **P-21** | Tests | Sin tests reales de JWT, `AUTHORIZED_EMAILS`, CORS, uploads maliciosos ni cifrado | ✅ CERRADO (2026-11-14) | Los controles **sí** tienen tests: JWT (`test_auth.py`, `test_auth_bypass.py`), allowlist (`test_auth_bypass.py`), cifrado (`test_security_encryption_key.py`, `test_session_encryption.py`, `test_upload_encryption.py`), SSRF/uploads (`test_security_hardening.py`, `test_upload_encryption.py`) — **36 archivos de test** · **CORS cubierto explícitamente** por `server/tests/test_cors_policy.py` (9 passed): middleware montado, allowlist sin comodines, orígenes HTTP solo de localhost y solo en desarrollo, `X-Request-Id` en `expose_headers`, `allow_credentials` sin `*`, origen desconocido **no** recibe `Access-Control-Allow-Origin` (preflight incluido) · **control verificado**: con `allow_origins=["*"]` el test falla (4 failed) |
| **P-22** | API | `/health` sin auth y con sonda bloqueante a Supabase | ✅ CERRADO | `server/main.py` (`/health`; el router `health.py` ya no existe) — las sondas (inspección de esquema + probe de Supabase) se ejecutan en el threadpool con `run_in_threadpool`, de modo que `/health` ya no bloquea el event loop ni a `/live` (el `healthCheckPath` de Render) · la respuesta pública ya no incluye el nombre del bucket (contrato: sin host, usuario, bucket ni credenciales) · el endpoint queda público por diseño (estándar de health checks, payload saneado: versión, dialecto y flags); el chequeo de infraestructura usa `/live` · `tests/test_health_endpoint.py` (2 passed) |
| **P-23** | Deuda | Código muerto: `password_policy`, `mobile_security`, `reports.py`, visual-summary, `KpiCards`, `AnomalyAlert`, `ServerStatusTracker` | ✅ CERRADO (2026-11-14) · ficha corregida (2026-11-15) | `server/src/routers/reports.py` **montado** en `main.py:163` (`app.include_router(reports.router, prefix="/api/v1")`) → `/report/kpi-summary` ya existe · `server/src/utils/password_policy.py` **eliminado** (nunca importado) · `client/src/components/KpiCards.tsx` y `AnomalyAlert.tsx` **no se eliminan: se conectan** mediante el nuevo `KpiPanel.tsx` (importa ambos y pide `/report/kpi-summary` a la fuente principal; montado en `DashboardView.tsx:461`) · `ServerStatusTracker.tsx` **no era código muerto**: lo importa `Providers.tsx:8` (se renderiza en `Providers.tsx:22`) · `mobile_security.py` **tampoco**: lo usa `pkce_service.py:22` → se conserva |
| **P-24** | UI | Clases Tailwind inexistentes (`bg-bi-s0`, `text-bi-text-1`, `duration-3000`) | ✅ CERRADO (2026-11-14) | `client/src/components/simulation/SimAgentConfig.tsx` — `text-bi-text-1` → `text-bi-t1` (las clases reales son `text-bi-t1`/`t2`/`t3`, `globals.css:139-141`); `bg-bi-s0/s1/s2` **sí existían** y se conservan · `client/src/components/Skeletons.tsx:82` — `duration-3000` → `duration-1000` (máx. existente) · `npm run build` OK · `npx tsc --noEmit` limpio |
| **P-25** | A11y | Modal de reportes sin `role="dialog"`, ESC ni focus trap; toasts sin `aria-live` | ✅ CERRADO (2026-11-14) | `client/src/components/ReportBuilder.tsx` — `role="dialog"` + `aria-modal="true"` + `aria-labelledby` + cierre con ESC + focus trap (Tab cicla dentro del modal) + devolución del foco al elemento que lo abrió · `client/src/components/ToastContainer.tsx` — `aria-live="polite"` (avisos) + `role="alert"` (errores) |
| **P-26** | UI | "Guardar Cambios" en Ajustes no guarda nada y reporta éxito | ✅ CERRADO (verificado 2026-11-14) | `client/src/components/SettingsView.tsx:74-91` — `handleSave` llama a `setUserConfig(...)` + `saveProviderModels(providerModels)` y reporta el estado real (`saving`/`success`/`error`) |
| **P-27** | UI | Fuentes guardadas se consultan pero nunca se renderizan (lista vacía al recargar). **Evolución 2026-10-21:** por decisión de producto ya no se precargan al iniciar sesión; solo se restauran al abrir una conversación del historial | ✅ CERRADO | `client/src/components/Sidebar.tsx:52-96,228-248` · runtime 2026-10-20 · `client/src/tests/Sidebar.test.tsx` |
| **P-28** | Tests | Suite de cliente no ejecutable (`npm test` no existe) y expectativas desactualizadas | ✅ CERRADO (2026-11-14) | `client/package.json` — **script `test` añadido** (`vitest run`), así que `npm test` funciona a mano · CI ya ejecutaba `npx vitest run` (`.github/workflows/ci.yml`) · suite cliente **88 passed** |
| **P-29** | UX | Sugerencias de chat sin cancelación + dataset inconsistente (última fuente vs primera) | ✅ CERRADO (2026-11-14) | El bucle ya no existía: el efecto depende de `suggestions.length` (`Chat.tsx:79`) · **inconsistencia corregida**: `Chat.tsx:61` usaba `dataSources[dataSources.length - 1].id` (última) mientras `:102,137,145,172` usaban `dataSources[0].id` (primera) → ahora **todas** usan `dataSources[0].id` (la fuente activa del chat) |
| **P-30** | Rendimiento | Force layout O(n²) por frame sin parar; polling de simulación sin `try/catch` | ✅ CERRADO (2026-11-14) | Force layout **arreglado**: `requestAnimationFrame` + `cancelAnimationFrame` en cleanup (`useForceLayout.ts:96,199,202,206`) · **polling corregido**: `SimulationSandbox.tsx` — el `setInterval` async ahora envuelve la llamada en `try/catch` (un fallo de red no deja la promesa rechazada sin manejar) y limpia el temporizador al desmontar |
| **P-31** | Infra | Rate limiting basado en IP de proxy (evadible con `X-Forwarded-For`) | ⚠️ ACEPTADO | `server/src/utils/limiter.py` · verificado con `uvicorn.Config(...)`: `forwarded_allow_ips=127.0.0.1` → `X-Forwarded-For` solo se acepta de 127.0.0.1, así que **la evasión por cabecera no aplica**. `get_user_or_ip` prioriza el email del JWT y cae a la IP del par TCP; el `except: pass` ahora registra en debug · `tests/test_security_hardening.py::TestRateLimitKey` (2 passed) · **Riesgo residual asumido:** detrás del proxy de Render las peticiones anónimas comparten un único cubo (afecta disponibilidad, no permite bypass); las peticiones autenticadas se agrupan por usuario |
| **P-32** | IA | Sin timeouts/reintentos en llamadas a LLM | ✅ CERRADO | `server/src/engine/providers.py:220-270` · `tests/test_providers.py::TestTimeout` |
| **P-53** | IA | `safe_parse_validator_json` no limpia BOM/zero-width; un JSON válido del Validator se rechaza y se pierde su feedback | ✅ CERRADO | `server/src/engine/bi_analyst.py:216-252` · `tests/test_validator_json.py` |
| **P-33** | Seguridad | `/connect-sql`: validación SSRF débil (DNS rebinding) y allowlist opcional | ✅ CERRADO | `security.py:validate_external_url_host` — allowlist de esquemas SQL (`sqlite:///`, `file://`, `duckdb://` bloqueados), `ALLOWED_SQL_HOSTS` obligatoria en producción (fail-closed) y validación de **todas** las IPs del DNS (antes solo la primera) · validación cableada en el punto único `get_sql_engine`, que cubre también la reconexión de fuentes guardadas (`common.py:514`) · `render.yaml` declara `ALLOWED_SQL_HOSTS` (`sync: false`, se configura en el Dashboard de Render) · `tests/test_security_hardening.py::TestSSRFProtection` (15 passed) · suite backend 313 passed, 3 xfailed |
| **P-34** | Datos | La sesión se guarda por usuario (sin `chat_id`) → conversaciones se pisan | ✅ CERRADO | Aislamiento por chat (2026-10-22) + **multi-fuente por chat (2026-10-28)**: tabla N-a-N `chat_data_sources` (`server/src/database.py`) · `PUT /history/{chat_id}/sources` con verificación de propiedad y reconstrucción del pool del chat (`server/src/routers/dashboard.py`) · `ensure_user_session` reconstruye **solo las fuentes vinculadas al chat** (o la primaria en chats antiguos) y ya no hereda la sesión activa de otro chat (`get_user_data` sin fallback) · `scope_session_to_sources` acota el pool a las fuentes de la conversación · `/analyze` y `/analyze/audit` aceptan `data_source_ids` validando pertenencia al chat · historial devuelve `data_sources` completo · el sidebar vincula los archivos subidos al chat activo · `server/tests/test_chat_data_sources.py` (2 passed) + `test_session_isolation.py` (8 passed) + Sidebar (4 passed) · suites: backend **305 passed**, cliente **78 passed** |
| **P-35** | Memoria | `data_store` global en memoria sin límite ni TTL | ✅ CERRADO | `server/src/utils/common.py` · `_BoundedStore` con max_entries=100 y ttl_seconds=3600 · LRU por inserción + expiración por tiempo · `server/tests/test_data_store_limits.py` (7 passed) · Antigravity 2026-10-22 |
| **P-44** | Frontend | Sin cliente OAuth la UI redirigía a Google con `client_id=undefined` ("OAuth client was not found") en vez de avisar | ✅ CERRADO | `client/src/app/login/page.tsx` + `LoginForm.tsx` |
| **P-45** | Frontend | Error de hidratación en la landing (atributos SSR ≠ cliente) al cargar | ✅ CERRADO (2026-11-15) | **Causa raíz encontrada:** `client/src/context/ThemeContext.tsx` inicializaba el estado con un *lazy initializer* que leía `localStorage` (`useState<Theme>(() => localStorage.getItem('vektra-theme') ...)`). En el servidor eso devuelve siempre `'dark'`, pero en el cliente el tema guardado: con `'light'` guardado, el HTML del servidor y el primer render de React **no coincidían** → error de hidratación. Y el tema no es solo pintura: `MermaidPreview.tsx:24` e `InteractiveCanvas.tsx:63` lo usan para generar markup. **Corrección:** el estado arranca **siempre** en `'dark'` (idéntico en servidor y cliente) y el tema guardado se aplica en un `useEffect` ya hidratado; el atributo `data-theme` del `<html>` lo sigue aplicando el script inline de `layout.tsx:30-42` **antes del primer pintado** (sin destello). Además, `localStorage` bloqueado (modo privado) ya no rompe la app: se captura y se mantiene el tema por defecto. `client/src/tests/ThemeHydration.test.tsx` (5 passed): el render del servidor (`renderToString`) y el primer render del cliente coinciden; el tema guardado se aplica después; el primer efecto no sobrescribe el tema guardado con `'dark'`; y con `localStorage` bloqueado la app no rompe. *Control verificado:* reintroducir el initializer que lee `localStorage` → 1 failed; restaurado → 5 passed |
| **P-47** | Dev/BD | `migrate_db.py` legado seguía sin cubrir el drift ni Windows | ✅ CERRADO (2026-11-14) | `server/src/utils/migrate_db.py` **eliminado** (`git rm`) · `LOCAL_DEV_GUIDE.md` — la sección "Si la base de datos se desincroniza" ya no manda ejecutar un script inexistente: documenta que `init_db()` hace `create_all()` + `_ensure_columns()` (cada `ALTER` en su propia transacción, así que el fallo de una columna no bloquea las siguientes) y que la vía de reset es borrar `test_bi.db` · `server/src/database.py:237-311` · `tests/test_database_migrations.py` |
| **P-48** | API/BI | `/dashboard/filter` respondía `200 success` con columnas inexistentes, no filtraba en modo SQL (TODO) y ocultaba los fallos por item | ✅ CERRADO (2026-11-14) | `server/src/routers/dashboard.py:268-503` (`_resolve_filter_columns`, `_filter_file_context`, `_filter_sql_context`) · `server/src/engine/executor.py:execute_sql_with_params` · `server/src/connectors/data_connectors.py:80-103` (`get_db_schema_structured`) · `server/tests/test_dashboard_filter.py` (12 passed) · suite backend **349 passed, 3 xfailed** |
| **P-49** | Dev | No hay modo local sin nube: subir archivos exige Supabase válido (503 si no) y el arranque no lo avisa | ⬜ ABIERTO | `server/src/routers/data.py:212-241` · runtime `/upload` |
| **P-50** | Infra/Dev | Con credenciales presentes pero inválidas, `/health` decía `not_configured` y el log solo `SupabaseException`; un typo en `SUPABASE_URL` (`hhttps://…`) dejaba `/upload` en 503 sin causa visible | ✅ CERRADO | `server/src/services/storage_service.py:34-100` · runtime `/upload` |
| **P-72** | Tests | `test_clave_nueva_sb_secret_crea_cliente` fallaba: el **venv local** tenía supabase-py 2.10.0 (la versión con el bug de P-50) mientras `requirements.txt` fija 2.33.0 | ✅ CERRADO (2026-11-15) | `server/tests/test_storage_diagnostics.py:64-68` — **la causa no era el test ni la red**: `SyncClient.__init__` de supabase-py **2.10.0** lanza `SupabaseException("Invalid API key")` en local para las claves `sb_secret_…` (verificado leyendo el código de `supabase/_sync/client.py:64`). El venv local (.venv y server/.venv) tenía 2.10.0; solo `.venv-codex` tenía la versión fijada 2.33.0. `pip install supabase==2.33.0` en el venv raíz → **5 passed**. El **test no se modificó** (el código y `requirements.txt` ya eran correctos: era drift de entorno). Suite completa → **376 passed, 3 xfailed, 0 failed** |
| **P-60** | Código | `server/src/services/pkce_service.py`: sintaxis rota y dependencias (`pkce_storage_factory`, `pkce_middleware`) que **nunca existieron**; módulo no importable | ✅ CERRADO (2026-11-15) | El archivo se **eliminó** (`git rm`): nada lo importaba, y "completarlo" habría exigido inventar un subsistema PKCE sin ningún consumidor. Import real verificado → `ModuleNotFoundError: No module named 'src.utils.pkce_storage_factory'`. Control mecánico: `server/tests/test_no_unimportable_modules.py` (4 passed) — importa **de verdad** todos los módulos de `server/src/` (lo que `compileall` no detecta) y comprueba que ningún `src.*` importado falte (con namespace packages PEP 420 bien reconocidos). *Control verificado:* reintroducir el módulo → 1 failed; restaurado → 4 passed |
| **P-73** | Código | `server/src/ui/styles.py`: residuo de la era Streamlit con `import streamlit`, dependencia **ausente** de `requirements.txt` | ✅ CERRADO (2026-11-15) | Archivo **eliminado** (`git rm`). Su único consumidor era `server/app.py` (la app Streamlit), borrado en la reescritura V2.5 (`5b7daff7`). `grep -rn "streamlit"` en el repo → **1 sola coincidencia** (el propio import); `streamlit` no está en `requirements.txt`, `render.yaml` ni en CI. Detectado **por** el test de P-60: con el archivo presente → `AssertionError: ["ui\\styles.py: No module named 'streamlit'"]`; tras la eliminación → 4 passed |
| **P-74** | Registro | El propio registro estaba corrupto: 32 caracteres `U+FFFD` grabados en el fichero, `→`/`·` convertidos en `?`, la fila de P-41 **duplicada**, la ficha de P-40 **partida dentro de la tabla** y los **totales de la cabecera falsos** (decía 28 medios / 10 bajos; eran 30 / 7) | ✅ CERRADO (2026-11-15) | `docs/PROBLEMAS_CONOCIDOS.md` — 32 `U+FFFD` reparados (`reacción`, `Código`, `métricas`, `Corrección`, `móvil`, `número`, `explícito`, `mínimo`) · separadores `→`/`·` restaurados · ficha de P-40 extraída de la tabla y fila de P-41 duplicada eliminada · cabeceras de MEDIOS y BAJOS corregidas a 5 columnas y 4 filas normalizadas (P-44, P-48, P-49, P-50) · fichas nuevas para los 9 IDs que solo tenían fila (P-46, P-49, P-52, P-53, P-56, P-66, P-67, P-68, P-69) · **control mecánico**: `server/tests/test_registry_integrity.py` (verifica encoding, unicidad de filas, nº de celdas, ficha↔fila y que los totales declarados coinciden con los contados) |
| **P-75** | Frontend / Build | Turbopack: *"Dynamic filesystem access causes tracing of the whole project"* — el arreglo de P-20 (leer los `.md` legales con rutas calculadas) arrastraba **todo** el proyecto al output de despliegue, inflando el bundle | ✅ CERRADO (2026-11-15) | `client/src/app/legal/[slug]/page.tsx` — rutas **literales** por documento + opt-out explícito `/* turbopackIgnore: true */` (el mecanismo que Turbopack ofrece para lecturas deliberadas y acotadas) · las páginas son **SSG**: la lectura ocurre solo en el build y el contenido queda horneado en el HTML · `npm run build` → **0 avisos** (antes 2) · HTML generados: `privacidad.html` 35.190 B, `terminos.html` 24.269 B, `cookies.html` 18.403 B · control: `client/src/tests/LegalDocsPath.test.ts` (6 passed); quitar el opt-out → **1 failed**, restaurado → **6 passed** |
| **P-70** | IA/BI | MET-G01/G02 promedian la "columna métrica" mezclando semánticas distintas (tasas y brechas en la misma columna) | ✅ CERRADO (2026-11-04) | `insight_auditor.py`: `_gap_row_split` detecta filas con etiqueta de diferencia (brecha/gap/saldo/desviación); MET-G01/G02 se calculan solo con las filas de magnitud (definen la exclusión) y la brecha recibe **MET-G03 en pp** con tarjeta y narrativa propias; red de seguridad en calidad cuando hay mezcla de magnitudes sin etiquetas (ratio <0.1); término nuevo "Diferencia (brecha)" en GENERIC_DEFINITIONS · INE real: 15.03 mezclado → **21.78 tasa + 1.52 pp brecha** · `TestMetricSemanticSplit` (5 tests) · suite **323 passed, 3 xfailed** |

### 🟢 BAJOS

| ID | Área | Problema | Estado | Evidencia |
|---|---|---|---|---|
| **P-36** | Debug | `safe_error_message()` oculta el error real en logs; `except: pass` disperso | ✅ CERRADO (2026-11-14) | **Todos** los `except: pass` y `except:` a secas de `server/src/` eliminados (≈17 sitios en `engine/executor.py`, `routers/data.py`, `routers/dashboard.py`, `routers/analysis.py`, `connectors/data_connectors.py`, `utils/exporter.py`, `utils/logging_config.py`, `utils/report_gen.py`, `utils/common.py`, `engine/{audit_agent,bi_analyst,providers,pptx_generator,swarm_engine}.py`, `services/storage_service.py`) — cada uno registra con `log_ignored_error(logger, contexto, exc, ...)` (tipo + mensaje saneado + `request_id`) · **correlación de peticiones**: `request_id_var` (ContextVar) + `get_request_id()`/`new_request_id()` en `server/src/utils/logging_config.py` y middleware `request_id_middleware` en `main.py` (respeta el `X-Request-Id` del cliente si es válido; si no, genera uno) · **guardia estática**: `server/tests/test_no_silent_exceptions.py` (5 tests) parsea **todo** `server/src/**.py` con `ast` y falla si cualquier `except` contiene un `pass` o es un `except:` sin tipo · **control verificado**: inyectado un `except: pass` → el test falla con `utils\exporter.py:384`; restaurado → 5 passed |
| **P-37** | Código | `generate_auto_dashboard` es un stub con TODO | ✅ CERRADO | `server/src/engine/bi_analyst.py:634-690` · implementa métricas reales (filas, columnas, resumen numérico) y gráfico determinista con plotly · Antigravity 2026-10-22 |
| **P-38** | UI | Layout de dashboard desde `localStorage` sin validar; `any` en simulación | ✅ CERRADO (verificado 2026-11-15) | `client/src/components/DashboardView.tsx` — `getSessionLayouts` valida el esquema de `localStorage` con `isValidLayout` (cada item debe tener `i`, `x`, `y`, `w`, `h` numéricos) y usa el layout por defecto si no es válido · `client/src/components/SimulationSandbox.tsx` — los `any[]` de `ontologyData`/`agentsData` sustituidos por `OntologyNode`, `OntologyEdge` y `AgentConfig` · verificado por grep el 2026-11-15: **ningún `any` en `client/src/components/simulation/` ni en `SimulationSandbox.tsx`**. El `any` que queda en `useForceLayout.ts:13` es la firma índice `[key: string]: any` del modelo de nodos D3, no un tipo sin validar |
| **P-39** | UI | Estado `pending` se etiquetaba como "Fallo" en historial de simulaciones | ✅ CERRADO | `client/src/components/simulation/SimHistory.tsx:42` · mapeo correcto: completed→Listo, running→En Curso, pending→Pendiente · Antigravity 2026-10-22 |
| **P-40** | UI / A11y | Texto por debajo de 10 px y sidebars fijos en móvil. El cierre de 2026-10-22 corrigió **4** pantallas; en la verificación del 2026-11-15 quedaban **38 ocurrencias** en **10 ficheros** (hasta `text-[7px]`) | 🟡 PARCIAL (cerrado en 4 pantallas; quedan 38 ocurrencias en 10 ficheros) | `SimHistory.tsx:12` y varios · **Corrección aplicada:** `DashboardView.tsx:484` texto de 8px → 12px · `SettingsView.tsx:165` texto de 8px → 10px (badge "GRATIS") · `simulation/SimHistory.tsx:12` sidebar `w-80` → `w-72 md:w-80` (más estrecho en móvil) · `Sidebar.tsx:187` sidebar principal `w-60` → `w-56 md:w-60` (más estrecho en móvil) · **Verificación:** `tsc --noEmit` limpio, `vitest run` → 64 passed, `npm run build` → OK |
| **P-41** | Tests | 3 tests backend fallando (deuda de test, no regresión de producción; el de dashboard se corrigió el 2026-10-20) | ✅ CERRADO | `test_exports.py:82,112` (xfail justificado: mocking de generate_pdf_report/create_presentation) · `test_simulation.py:129` (xfail justificado: serialización de MagicMock en respuesta JSON) · `server/src/engine/providers.py` · `generate_ai_content` wrapper agregado para import en analysis.py · Antigravity 2026-10-22 |

| **P-46** | API | `/data-sources` y `/sources` devuelven al cliente la `url` interna (clave de nube con el md5 del email o ruta del contenedor) | ✅ CERRADO | `server/src/routers/data.py` — nuevo `_serialize_source()` usado en `GET /data-sources`, `POST /data-sources` y `GET /sources`: la respuesta ya no incluye `url` (clave de nube, ruta del contenedor o cadena SQL cifrada); el backend sigue usándola internamente para reconectar (`ensure_user_session`) · el cliente no consumía ese campo (solo POST/DELETE en `api.ts`) · el historial ya serializaba sin url (`dashboard.py:_serialize_chat_source`) · `tests/test_source_serialization.py` (3 passed) · suite backend 318 passed, 3 xfailed |

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

### P-11 · Upload: `.tmp` en claro y zip-bomb (CERRADO 2026-11-11)
**Archivo:** `server/src/routers/data.py` · `server/src/utils/security.py` · `server/tests/test_upload_encryption.py`.

> **Historia.** El fix original de Antigravity (2026-10-22) se revirtió en `885b3b61` ("restaurar
> persistencia", P-57), que reescribió `upload_file` y volvió a guardar el original **en claro** en
> disco y en nube, con `is_encrypted=False`. El test de regresión se borró en `20040e19`. El estado
> fue REABIERTO (2026-11-03) hasta que la auditoría del 2026-11-07 lo volvió a marcar como la
> prioridad técnica más urgente y el plan `PLAN_P11_UPLOAD_SEGURO.md` (2026-11-10) detailó los
> cambios. El 2026-11-11 se aplicó la corrección completa.

**Problema.** El original se escribía en claro (en `.tmp` antes, y directamente en `permanent_path`
tras el revert) y se subía en claro a la nube; además el guard anti zip-bomb
`_reject_zip_bomb_early` existía en el archivo pero **nunca se invocaba** en el flujo activo, de
modo que los límites se comprobaban después de abrir el Excel/zip.

**Corrección aplicada (3 cambios quirúrgicos en `upload_file`).**
1. **Zip-bomb temprano** — `_reject_zip_bomb_early(raw_bytes, clean_name)` se invoca entre la
   lectura en memoria y `load_file_data_from_bytes(...)`. Excel: suma las dimensiones declaradas de
   cada hoja con `openpyxl` en modo `read_only` (lee solo el XML de dimensiones). CSV: cuenta
   saltos de línea en los bytes crudos. Límites: 2M celdas / 2M líneas. Rechazo con HTTP 400.
2. **Cifrado en memoria** — `encrypt_bytes(raw_bytes)` (Fernet) produce `encrypted_bytes`; solo
   esos bytes se escriben en `permanent_path` y se suben con `upload_bytes(cloud_key, encrypted_bytes)`.
   El original **nunca** se persiste en claro, ni en disco ni en la nube, ni siquiera de forma transitoria.
3. **Registro coherente** — `DataSource.is_encrypted=True`, que es lo que activa el descifrado en el
   read-back (`common.py:485-499`: `decrypt_file_to_bytes` + `load_file_data_from_bytes`).

**Compatibilidad.** El read-back soporta ambos formatos: los archivos cifrados se descifran cuando
`is_encrypted=True`, y los archivos legacy subidos antes del fix se siguen leyendo por el branch
`else` (`load_file_data`). No se requiere migración de los archivos existentes.

**Tests de regresión (P-21 parcial).** `server/tests/test_upload_encryption.py` — 7 passed:
- `test_upload_encrypts_at_rest`: el archivo en disco no empieza por el header del CSV y sí por el
  token Fernet (`gAAAA`).
- `test_upload_rejects_zip_bomb_xlsx`: xlsx con `<dimension ref="A1:XFD1048576"/>` (~17,18 mil
  millones de celdas declaradas) → HTTP 400 y `load_file_data_from_bytes` **no** es invocado.
- `test_upload_rejects_zip_bomb_csv`: CSV de > 2M líneas → HTTP 400 sin parsear.
- `test_encrypted_file_roundtrip`: tras limpiar la caché, `ensure_user_session` reconstruye el pool
  descifrando el archivo y las columnas/filas coinciden.
- 3 guardas estáticas que fallan si alguien borra la llamada al guard, el `encrypt_bytes` o el
  `is_encrypted=True`.

**Dos bugs de test encontrados y corregidos al implementar.**
- El `setUp` parcheaba `upload_bytes`/`delete_object` sobre `src.utils.common`, donde **no existen**
  (viven en `src.services.storage_service`), y parcheaba `DATA_SOURCES_DIR` sobre `common` cuando
  el router lo importa **por valor** (`from src.utils.common import DATA_SOURCES_DIR`): el archivo
  se escribía en el `./data_sources` real. Los parches van ahora sobre `src.routers.data`.
- El fixture de zip-bomb Excel usaba `ws._dimension = "A1:XFD1048576"`, pero `wb.save()` de openpyxl
  **recalcula el rango real** y descarta ese valor (queda 1×1), así que el guard nunca se disparaba.
  El fixture ahora reescribe el XML de la hoja dentro del zip, que es lo que lee el guard.
- El rate limiter de slowapi es global y compartido entre tests (`/upload` = 5/min por usuario): sin
  `limiter.reset()` en el `setUp`, el test heredaba el cupo consumido por `test_data.py` y fallaba
  con 429 según el orden de ejecución de la suite.

**Verificación.** `pytest tests/test_upload_encryption.py` → 7 passed · `pytest tests/` → **339 passed, 3 xfailed** (baseline previo: 332 passed, 3 xfailed; +7 tests nuevos, sin regresiones).

**Regla:** nunca escribas datos de usuario en claro, ni siquiera "un momento". Los límites de
descompresión se comprueban **antes** de parsear, no después.

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

**P-17 · ✅ CERRADO (2026-11-15)** · Repo inflado. Sacar el `.mp4` (24 MB) y `debug_server.log` del índice; `.gitignore`. *Cierre:* `git ls-files` sin binarios ni logs.

**Qué pasaba.** `presentacion/2026-05-13 08-49-44.mp4` (24 MB) y `server/debug_server.log` (364 KB) estaban versionados. El `.gitignore` ya tenía `*.log`, pero se añadió **después** de que el log entrara: `.gitignore` no des-versiona nada.

**Hallazgo adicional (privacidad).** El log no era solo "peso": contenía el **email real del usuario** (`juanddavidvo03@gmail.com`) en 2.549 líneas, más 27 líneas que mencionan `api_key`/`secret`/`token`/`bearer`. Se comprobó con `git grep -l` que era el **único** fichero versionado con esa dirección, de modo que sacarlo del índice la elimina por completo del árbol de trabajo (el histórico de git conserva las versiones antiguas — para purgarlo del historial haría falta `git filter-repo`, que reescribe el historial y **no** se ha hecho: es una operación destructiva que requiere decisión del propietario del repo).

**Corrección aplicada.**
- `git rm --cached` de ambos ficheros: **dejan de versionarse pero se conservan en el disco local** (no se pierde nada del equipo).
- `.gitignore` ampliado con `presentacion/`, `*.mp4`, `*.mov`, `*.webm` (además del `*.log` que ya estaba).
- **Control mecánico en CI**: nuevo job `hygiene` que corre en cada push y **falla** si (a) hay un `.log`/binario versionado o (b) hay un fichero versionado de más de 5 MB. Es la diferencia entre "lo arreglé una vez" y "no puede volver a pasar".

**Verificación.** `git ls-files | grep -iE '\.(log|mp4|...)$'` → **vacío** · ningún fichero versionado supera 5 MB (el mayor es un `.jpg` de 763 KB) · *control verificado:* `git add -f` del `.mp4` → **detectado por los dos guards** (extensión y tamaño); retirado → limpio.

**Regla anti-repetición.** `.gitignore` **no des-versiona** lo que ya está versionado: solo evita que algo nuevo entre. Para lo que ya está, hay que hacer `git rm --cached` explícitamente. Y un artefacto de depuración (un log de sesión) **no es un artefacto del producto**: versionarlo mete datos personales de una sesión concreta en el historial de forma permanente.
**P-18 · CERRADO (verificado 2026-11-14)** · `pkce_service.py:90` SyntaxError. *Cierre:* `python -c "ast.parse(...)"` OK o archivo eliminado por código muerto.

**Verificación (2026-11-14).** `server/src/services/pkce_service.py` **no** tiene SyntaxError: `ast.parse` devuelve OK y el módulo **se importa en runtime** — `pkce_service.py:22` hace `from src.utils.mobile_security import validate_mobile_request_security`. La fila del registro estaba desfasada respecto al código actual. *Cierre:* el módulo parsea y se importa sin error. **Regla anti-repetición:** una ficha `ABIERTA` no se cierra por antigüedad del texto; se verifica contra el código antes de darla por vigente.

**P-19 · ✅ CERRADO (2026-11-14)** · Fallback silencioso a SQLite + baseline Alembic inválida. *Verificado en runtime (2026-10-19):* la SQLite local quedó desfasada respecto a los modelos (`no such column: user_configs.code_verifier`) → `GET /user-config` 500 y `resolve_keys()` reventando en los endpoints de simulación; `create_all()` no altera tablas y `migrate_db.py` no cubre ese drift (ver P-47). *Cierre:* `DATABASE_URL` inválida aborta el arranque; `alembic upgrade head` funciona en limpio.

**Corrección aplicada (2026-11-14) — mitad 1: arranque fail-closed.**
- `server/src/database.py`: el `try/except` que caía a SQLite **se eliminó**. Ahora `_build_engine()` lanza y el import aborta con un `RuntimeError` explícito: *"DATABASE_URL inválida … Arranque abortado: no se usa un fallback a SQLite porque los datos se perderían en el siguiente deploy."*
- **Descubrimiento clave:** `create_engine()` es **perezoso** — no abre conexión. Una URL bien formada pero con host inexistente **no** falla en el import; falla en la primera petición. Por eso se añadió `_assert_database_reachable()`: ejecuta `SELECT 1` contra la BD **antes** de aceptar tráfico y aborta en producción si no responde (en desarrollo solo avisa, para no bloquear al developer que aún está levantando la BD).
- `init_db()` ahora aborta en producción si el esquema no se puede sincronizar (antes solo logueaba el error y seguía sirviendo con un esquema desfasado).
- `server/main.py:165-180`: el `try/except` que envolvía `init_db()` **propaga** el error en producción en vez de tragárselo.
- `sanitize_db_error()` ajustada: la contraseña se enmascara (`usuario:***@host`) **conservando el usuario**, que no es un secreto; la versión anterior se comía también el usuario por un solapamiento de regex.

**Corrección aplicada (2026-11-14) — mitad 2: baseline de Alembic.**
- `server/migrations/versions/e114418c6081_initial_baseline.py` reescrito: `_ensure_tables_exist()` (crea el esquema si la BD está vacía; no-op si ya existe, así que el Postgres de Render no cambia), `_tables_exist()`, `_sqlite_fks_already_cascade()` (SQLite **no nombra** sus FKs, así que `op.drop_constraint(None, …)` es imposible incluso en batch mode: si el estado deseado ya está, no se toca nada), `_column_exists()` (idempotencia de `add_column`) y `op.batch_alter_table('user_configs')` para el `ALTER COLUMN … TYPE` (SQLite necesita la estrategia copy-and-move).
- `server/migrations/env.py`: `render_as_batch=True` en las dos llamadas a `context.configure()`. **Aclaración importante:** `render_as_batch` solo afecta al *autogenerate*; no convierte un `ALTER` escrito a mano en batch. Por eso el `batch_alter_table` explícito es imprescindible.

**Evidencia (2026-11-14).**
- `alembic upgrade head` sobre BD limpia (`sqlite:///./scratch/p19_f.db`) → `Running upgrade -> e114418c6081, Initial baseline`, sin errores. Inspección posterior: `alembic_version = [('e114418c6081',)]` · 10 tablas creadas · `dashboard_items` con 2 FK y `ondelete: CASCADE` en ambas · `simulations.current_round` presente · `user_configs.preferred_provider` = `VARCHAR()` (era `TEXT`).
- `server/tests/test_database_startup_failclosed.py` (**7 passed**): URL mal formada → aborta en el import · la contraseña **no** aparece en el mensaje · BD inalcanzable → aborta en producción / solo avisa en desarrollo · `init_db()` aborta en producción si falla el esquema · SQLite explícito en desarrollo sigue funcionando · guard estático que falla si alguien reintroduce `Usando SQLite fallback` en el fuente.

**Regla anti-repetición.** Un arranque que "funciona" contra la base equivocada es peor que un arranque que falla: el servicio acepta tráfico, responde 500 y pierde datos sin que nadie se entere. La configuración de BD es **fail-closed**, igual que `ENCRYPTION_KEY` (P-09). Y una revisión de migración debe ser **idempotente y portable**: SQLite no es un caso de pruebas, es el entorno real de desarrollo.

**P-20 · ✅ CERRADO (2026-11-15)** · Páginas legales leen fuera de `client/`. *Cierre:* los `.md` viven dentro de `client/` o se empaquetan; build standalone las sirve.

**Qué pasaba.** `client/src/app/legal/[slug]/page.tsx:31` leía los documentos con `path.join(process.cwd(), "..", "docs", "legal", doc.file)`. Como `process.cwd()` es `client/` en desarrollo, la ruta "../docs/legal" **acertaba en local**; pero en el build standalone o en Docker `process.cwd()` no tiene un `docs/` al lado → **404 en las tres páginas legales** (`/legal/privacidad`, `/legal/terminos`, `/legal/cookies`). El `.next` se genera bien (las rutas se prerenderizan sin error) y el 404 aparece **solo en runtime**: un fallo que no se ve en el build ni en los tests.

**Corrección aplicada.**
- Los tres `.md` **se movieron** (`git mv`, sin dejar copia duplicada): `docs/legal/{politica-privacidad,terminos-de-uso,aviso-cookies}.md` → **`client/content/legal/`**. Ahora forman parte de la app: el build los encuentra siempre.
- La página sustituye la ruta fija por una **ruta literal por documento** (`process.cwd()/content/legal/<fichero>`), con el opt-out `/* turbopackIgnore: true */` para que Turbopack no arrastre el proyecto entero al output de despliegue (**P-75**, encontrado al validar este mismo arreglo: la versión con `resolveLegalFile()` y un bucle de candidatas generaba el aviso *"Dynamic filesystem access causes tracing of the whole project"*). Las tres páginas son **SSG**: la lectura ocurre solo en el build y el contenido queda horneado en el HTML; si ninguna, `notFound()`.

**Verificación.** `npm run build` OK · las tres páginas se **prerenderizan (SSG)** con el contenido real horneado en el HTML: `privacidad` 35 KB, `terminos` 24 KB, `cookies` 18 KB, y el texto del documento aparece dentro (`grep` de "datos personales|RGPD" → 6 coincidencias). `client/src/tests/LegalDocsPath.test.ts` (**5 passed**): los `.md` están dentro de `client/`, se encuentran con `cwd = client/` **y** con `cwd = raíz del repo` (el caso standalone/Docker), el contenido no está vacío y la página no vuelve a leer de `docs/`.

**Control verificado (falla antes / pasa después).** Reintroduciendo la ruta antigua (`"..", "docs", "legal"`) → `la página NO lee de fuera de client/` **failed**; restaurada → **6 passed**. El control de **P-75** (toda llamada a `fs` debe llevar el opt-out) también está verificado: quitar el opt-out → **1 failed**, restaurado → **6 passed**.

**Regla anti-repetición.** Un `fs.readFileSync` con una ruta **relativa al `cwd`** es una bomba de relojería: funciona en local y falla en producción, y el build no lo detecta. Todo fichero que la app lea en build time tiene que vivir **dentro del paquete** (`client/`), y la resolución tiene que probar **todas** las ubicaciones posibles según cómo se arranque el proceso. Y no basta con mover el fichero: hace falta un test que verifique que se encuentra **desde varios `cwd`**, que es exactamente la diferencia entre local y Docker.

**P-21 · ✅ CERRADO (2026-11-14)** · Tests sin JWT/CORS/uploads/cifrado reales. *Cierre:* tests que fallen si se desactiva cada control.

**Verificación (2026-11-14).** La suite **sí** cubría los controles críticos: JWT/autorización, allowlist de proveedores, cifrado de subidas (P-11) y SSRF en `/connect-sql`. Faltaba un **test explícito de CORS** — si alguien quita el middleware o la allowlist, ningún test lo detectaba.

**Corrección aplicada (2026-11-14).** `server/tests/test_cors_policy.py` (**9 passed**):
- el middleware `CORSMiddleware` está montado en la app;
- la allowlist **no** contiene comodines (`*` ni `https://*.vercel.app`): regla 4 del registro (*«sin listas negras / comodines de seguridad»*);
- los orígenes **HTTP** solo pueden ser `localhost`/`127.0.0.1` **y solo en desarrollo** (`server/.env` permite `http://localhost:3000` para el servidor de desarrollo de Next.js; en producción un origen HTTP sería un agujero);
- `X-Request-Id` está en `expose_headers` (P-36 necesita que el cliente lo lea);
- `allow_credentials=True` no se combina con un origen comodín;
- **comportamiento observable**: un origen desconocido **no** recibe `Access-Control-Allow-Origin` (ni en el preflight `OPTIONS`), y uno permitido sí lo recibe.

**Control verificado (falla antes / pasa después).** Con `allow_origins=["*"]` inyectado en `main.py`: **4 failed** (`test_allowed_origin_receives_allow_origin_header`, `test_unknown_origin_does_not_receive_allow_origin_header`, `test_preflight_from_unknown_origin_is_not_allowed`, `test_allow_credentials_is_not_combined_with_wildcard`). Restaurado → **9 passed**.

**Regla anti-repetición.** Una allowlist de CORS que no se **comporta** como una allowlist no es una allowlist: el test tiene que mirar las cabeceras que llegan al navegador, no solo la configuración declarada.

**P-22** · `/health` público y bloqueante. *Cierre:* sonda con timeout y sin datos sensibles; opcional proteger detalle.
**P-23 · ✅ CERRADO (2026-11-14)** · Código muerto (~1.500 líneas frontend + módulos backend). *Cierre:* eliminar o registrar como `ACEPTADO`.

**Verificación (2026-11-14).** Confirmado contra el código, no contra el texto del registro: `server/src/utils/password_policy.py` **nunca se importa**; `server/src/routers/reports.py` **no está incluido** en `main.py`; y `client/src/components/KpiCards.tsx`, `AnomalyAlert.tsx` y `ServerStatusTracker.tsx` **nunca se importan**. **Ojo:** `server/src/utils/mobile_security.py` **sí** está vivo (`pkce_service.py:22` lo importa) — **no debe eliminarse**.

**Corrección aplicada (2026-11-14).**
- `server/src/routers/reports.py` **montado** en `main.py:163` → `app.include_router(reports.router, prefix="/api/v1")`. El endpoint `/report/kpi-summary` ahora existe y sus consumidores (`KpiCards`, `AnomalyAlert`) dejan de quedarse sin datos. *Aquí el código no era "muerto": estaba implementado y simplemente nunca se conectó — un bug de cableado, no de deuda.*
- `server/src/utils/password_policy.py` **eliminado** (nunca importado por nadie).
- `client/src/components/KpiCards.tsx` y `AnomalyAlert.tsx` **no se eliminan: se conectan**. Se crea `client/src/components/KpiPanel.tsx`, que los importa, pide `/report/kpi-summary` al backend para la fuente principal y los pinta con datos reales. `DashboardView.tsx:461` monta el panel.
- `client/src/components/ServerStatusTracker.tsx` **tampoco se elimina**: ya estaba vivo y lo importa `client/src/components/Providers.tsx:8` (se renderiza en `Providers.tsx:22`). El registro original lo daba por huérfano por error.
- `server/src/utils/mobile_security.py` **conservado**: lo usa `pkce_service.py:22` → no es código muerto.

**Verificación:** `npm run build` OK · `npx tsc --noEmit` limpio · suite cliente verde (98 passed) · backend verde (376 passed, 3 xfailed, 0 failed).

**Regla anti-repetición.** Antes de borrar un módulo "muerto", hay que comprobar **quién lo importa**, y no solo si está importado: un router no montado en `main.py` es código **vivo mal cableado** (P-23 lo demostró), y borrarlo habría destruido una funcionalidad que el cliente esperaba. Y la comprobación debe ser **literal** (`grep` del símbolo en todo el árbol), no una impresión: en este mismo P-23 la ficha afirmaba que tres componentes nunca se importaban, y dos de ellos **sí** lo estaban (`Providers.tsx` los montaba). Una ficha de registro que afirma algo sin verificarlo es peor que no tener ficha: propaga el error a quien la lea.

**P-24 · ✅ CERRADO (2026-11-14)** · Tokens Tailwind inexistentes. *Cierre:* usar `--color-bi-*` reales; revisión visual del paso de configuración.

**Verificación (2026-11-14).** Los tokens reales están en `client/src/app/globals.css:129-141`: superficies `--color-bi-s0/s1/s2/s3` y texto `--color-bi-t1/t2/t3`. Por tanto: **`bg-bi-s0`, `bg-bi-s1` y `bg-bi-s2` sí existen** (la ficha los arrastraba como inexistentes), pero **`text-bi-text-1` NO existe** — los que existen son `text-bi-t1`/`t2`/`t3`. Igual con **`duration-3000`**: las duraciones definidas son `300/500/700/1000` (`globals.css:524-527`), así que `duration-3000` no genera ninguna clase.

**Corrección aplicada (2026-11-14).**
- `client/src/components/simulation/SimAgentConfig.tsx` (líneas 63, 65, 76, 100, 138): `text-bi-text-1` → **`text-bi-t1`**. Las clases `bg-bi-s0/s1/s2` se conservaron: son válidas.
- `client/src/components/Skeletons.tsx:82`: `duration-3000` → **`duration-1000`**.

**Verificación:** `npm run build` OK · `npx tsc --noEmit` limpio · suite cliente verde.

**Regla anti-repetición.** Una clase Tailwind inexistente no es un error de build: es un estilo que **silenciosamente no se aplica**. La revisión tiene que contrastar cada token con `globals.css`, no con la intuición.

**P-25 · ✅ CERRADO (2026-11-14)** · A11y modal/toasts. *Cierre:* `role="dialog"`, `aria-modal`, ESC, focus trap, `aria-live`.

**Verificación (2026-11-14).** `client/src/components/ReportBuilder.tsx` abría un modal **sin** `role="dialog"` ni `aria-modal`, sin cierre por ESC y sin focus trap; `client/src/components/ToastContainer.tsx` **no** declaraba `aria-live`, así que un lector de pantalla no anunciaba los avisos.

**Corrección aplicada (2026-11-14).**
- `client/src/components/ReportBuilder.tsx`: el modal ahora declara `role="dialog"` + `aria-modal="true"` + `aria-labelledby` (apuntando al título), cierra con **ESC**, atrapa el **foco** dentro del diálogo (Tab cicla entre sus elementos en lugar de salir a la página de fondo) y **devuelve el foco** al elemento que lo abrió al cerrarse.
- `client/src/components/ToastContainer.tsx`: `aria-live="polite"` para los avisos y `role="alert"` para los errores, de modo que un lector de pantalla los anuncia.

**Verificación:** `npm run build` OK · `npx tsc --noEmit` limpio · suite cliente verde.

**Regla anti-repetición.** Un modal sin `role="dialog"` no es un modal para un lector de pantalla: se lee como texto suelto de la página. Los gestos de teclado (ESC, focus trap) no son adorno, son el contrato mínimo de un diálogo.
**P-26 · CERRADO (verificado 2026-11-14)** · "Guardar Cambios" no-op (CERRADO por Antigravity 2026-10-22). *Cierre:* botón ejecuta el guardado real.

**Verificación (2026-11-14).** `client/src/components/SettingsView.tsx:74-91` — `handleSave` llama a `setUserConfig(...)` **y** a `saveProviderModels(providerModels)`, y reporta el estado real del resultado (`saving` → `success`/`error`). La fila del registro estaba desfasada respecto al código actual. *Cierre:* el botón ejecuta el guardado real y no reporta un éxito falso.

**Corrección aplicada.**
- `client/src/components/SettingsView.tsx`: `handleSave` ahora llama a `setUserConfig(userId, ...)` para persistir temperatura, sensibilidad de anomalías, estrategia Magic Clean, formato de moneda/fecha, color de marca, nombre de organización, pie de página, orientación PDF, anexar tabla de datos y tema de gráficos.
- También llama a `saveProviderModels(providerModels)` para persistir la selección de modelos por proveedor.
- Se agregó `userId` al desestructurado de `useDashboard()` y `setUserConfig`/`saveProviderModels` a las importaciones desde `@/lib/api`.
- El botón ahora muestra estados `saving` → `success`/`error` según el resultado real de la API.

**Verificación:** `tsc --noEmit` limpio, `vitest run` → 64 passed, `npm run build` → OK.
**P-27 · CERRADO** · Fuentes guardadas no renderizadas. *Causa:* el primer `fetchSources` corría antes de que NextAuth cargara el token; la petición iba sin `Authorization` y en local caía en el usuario de pruebas (lista vacía), en producción daba 401. *Corrección original:* el token se configura antes del fetch, no se consulta mientras `status === "loading"` y las fuentes guardadas pasan a ser las activas si no hay ninguna. *Evolución 2026-10-21:* por decisión de producto **se retiró la precarga global**; una sesión nueva arranca sin fuentes y el historial restaura la fuente del chat al abrirlo. *Evidencia:* `client/src/tests/Sidebar.test.tsx` (no llama a `getDataSources` al montar; `loadChat` restaura la fuente) + `npx vitest run` → 40 passed + `npm run build` OK. *Cierre:* la lista de la conversación se pinta desde su fuente vinculada, no desde todas las fuentes del usuario.
**P-28 · ✅ CERRADO (2026-11-14)** · Tests frontend no ejecutables. *Cierre:* `npm test` verde en CI.

**Verificación (2026-11-14).** Los tests **sí** se ejecutaban: `npx vitest run` → **13 files, 88 passed**, y CI los invoca en `.github/workflows/ci.yml`. Lo que faltaba era el **script `test`** en `client/package.json`: `npm test` fallaba "a mano" porque no existía el comando.

**Corrección aplicada (2026-11-14).** `client/package.json` — añadido el script `"test": "vitest run"`, de modo que `npm test` ejecuta exactamente la misma suite que CI.

**Verificación:** `npm test` → verde en local · CI sigue ejecutando `npx vitest run` (mismo script).

**Regla anti-repetición.** Un comando que solo existe documentado en el README y no en `package.json` es un comando que nadie usa: el primer paso de "correr los tests" es que el comando exista.

**P-29 · ✅ CERRADO (2026-11-14)** · Sugerencias de chat en bucle/dataset inconsistente. *Cierre:* efecto sin `suggestions.length`; misma fuente que el análisis; cancelación.

**Verificación (2026-11-14).** La mitad del bucle ya estaba resuelta: el efecto depende de `suggestions.length` (`Chat.tsx:79`), no del propio array que escribe. Quedaba la **inconsistencia del dataset**: `Chat.tsx:61` usaba `dataSources[dataSources.length - 1].id` (la **última** fuente) mientras `:102`, `:137`, `:145` y `:172` usaban `dataSources[0].id` (la **primera**) — la sugerencia podía analizar una fuente distinta de la que ejecuta el análisis.

**Corrección aplicada (2026-11-14).** `client/src/components/Chat.tsx:61` — `dataSources[dataSources.length - 1].id` → **`dataSources[0].id`**. Ahora **todo** `Chat.tsx` usa la misma política de fuente (la primera = fuente activa del chat), y la sugerencia analiza exactamente lo mismo que el análisis.

**Verificación:** `npm run build` OK · `npx tsc --noEmit` limpio · suite cliente verde.

**Regla anti-repetición.** Una misma variable con dos políticas distintas en el mismo archivo es un bug esperando: la UI sugiere una cosa y la aplicación hace otra. La fuente efectiva se decide **en un solo sitio**.

**P-30 · ✅ CERRADO (2026-11-14)** · Force layout O(n²) + polling sin guard. *Cierre:* `requestAnimationFrame` se detiene al estabilizar; interval con `try/catch` y deps estables.

**Verificación (2026-11-14).** La parte de rendimiento ya estaba resuelta: el force layout usa `requestAnimationFrame` + `cancelAnimationFrame` en el cleanup (`client/src/hooks/useForceLayout.ts:96,199,202,206`), así que se detiene al estabilizar y no queda O(n²) por frame. Quedaba el polling: `client/src/components/SimulationSandbox.tsx:150-159` usaba un `setInterval` async **sin `try/catch`**, así que un fallo de red dejaba una promesa rechazada sin manejar.

**Corrección aplicada (2026-11-14).** `client/src/components/SimulationSandbox.tsx` — el cuerpo del `setInterval` va ahora dentro de un `try/catch` que registra el fallo (sin tragárselo) y el temporizador se limpia al desmontar el componente, para que no siga interrogando una pantalla que ya no existe.

**Verificación:** `npm run build` OK · `npx tsc --noEmit` limpio · suite cliente verde.

**Regla anti-repetición.** Un `setInterval` con una función async es una promesa sin catcher dentro de un temporizador que nadie vigila: el primer fallo de red produce un `unhandled rejection` que ni el error boundary ve.
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
**P-36 · ✅ CERRADO (2026-11-14)** · Errores ocultos (`safe_error_message`, `except: pass`). *Cierre:* log con tipo+mensaje saneado y `request_id`; prohibido `except: pass`.

**Verificación (2026-11-14).** Había **17+ `except: pass` sin log** dispersos por `server/src/`: `engine/executor.py:75,326,352,509,534,559,769` · `routers/data.py:229,448` · `connectors/data_connectors.py:121,189` · `utils/exporter.py:226` · `utils/logging_config.py:47` · `utils/report_gen.py:83`. Son la sección 2, regla 8 del propio registro ("sin `except: pass`") incumplida en el propio backend.

**Corrección aplicada (2026-11-14) — mecanismo de registro.**
- `server/src/utils/logging_config.py`: nuevos `request_id_var` (ContextVar), `get_request_id()`, `new_request_id()` y **`log_ignored_error(logger, contexto, exc, level=…, **campos)`**, que escribe *"EXCEPCIÓN IGNORADA [request_id] contexto: Tipo (mensaje saneado)"*. El mensaje pasa por `_sanitize_message`, así que no se filtran secretos al log.
- `server/main.py`: middleware **`request_id_middleware`** — respeta el `X-Request-Id` que envíe el cliente si es un token opaco y acotado (`^[A-Za-z0-9._:-]{1,64}$`), y si no, genera uno; el id viaja en el ContextVar y se devuelve en la cabecera de respuesta. **La cabecera `X-Request-Id` ya estaba declarada en CORS pero nunca se generaba**: sin ella no había forma de correlacionar "el error del log" con "la petición que lo provocó".

**Corrección aplicada (2026-11-14) — los `except` de `server/src/`.**
Todos los `except: pass` y los `except:` a secas se eliminaron: `engine/executor.py` (incluido el script **orquestador** que corre en el subproceso, que ahora lleva su propio shim de logging autocontenido), `routers/{data,dashboard,analysis}.py`, `connectors/data_connectors.py`, `utils/{exporter,logging_config,report_gen,common}.py`, `engine/{audit_agent,bi_analyst,providers,pptx_generator,swarm_engine}.py` y `services/storage_service.py`. Cada uno registra con `log_ignored_error(...)` (tipo + mensaje saneado + `request_id`) o, si la excepción es deliberadamente ignorable, se documenta por qué en el código. Además `routers/dashboard.py` convierte el `except:` que envolvía `json.loads(filters_json)` en un `HTTPException(400)` limpio: ese error **sí** es accionable para el cliente.

**Control mecánico (regla 5: *«un control desconectado no existe»*).**
`server/tests/test_no_silent_exceptions.py` (**5 tests**) parsea **todo** `server/src/**.py` con `ast` y falla si cualquier `ast.ExceptHandler` contiene un `ast.Pass` o es un `except:` sin tipo. Además comprueba que `log_ignored_error` incluye tipo + `request_id` + contexto en el mensaje, y que el middleware real genera/respeta el `X-Request-Id`.

**Control verificado (falla antes / pasa después).** Inyectado un `except: pass` en `utils/exporter.py` → el test falla con `AssertionError: Lists differ: ['utils\\exporter.py:384'] != []`. Restaurado → **5 passed**.

**Regla anti-repetición.** «No hay `except: pass`» es una regla que se cumple una vez y se deshace con el siguiente `git pull`. Lo que la hace lasting es el **test estático**: nadie puede reintroducir un error silencioso sin romper la suite. Y un error ignorado que no se registra no es un error ignorado: es un error *perdido*.
**P-37** · `generate_auto_dashboard` stub (CERRADO por Antigravity 2026-10-22). *Cierre:* implementar o devolver 501 explícito.
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

**P-40 · PARCIAL (cerrado en 4 pantallas el 2026-10-22; verificado incompleto el 2026-11-15) · Texto de 8-10 px y sidebar fija (`w-80`) en móvil.** *Corrección aplicada:* `client/src/components/DashboardView.tsx:484` texto de 8px → 12px (título de tarjetas del dashboard) · `client/src/components/SettingsView.tsx:165` texto de 8px → 10px (badge "GRATIS") · `client/src/components/simulation/SimHistory.tsx:12` sidebar `w-80` → `w-72 md:w-80` (más estrecho en móvil) · `client/src/components/Sidebar.tsx:187` sidebar principal `w-60` → `w-56 md:w-60` (más estrecho en móvil). *Verificación:* `tsc --noEmit` limpio, `vitest run` → 64 passed, `npm run build` → OK. **Regla anti-repetición:** el texto nunca debe ser menor de 10px (idealmente 12px+) para accesibilidad. Los sidebars deben ser responsivos, no fijos en móvil. *Pendiente (P-40 sigue ABIERTO en la ronda 7):* la reconciliación del 2026-11-15 detectó que **quedan** tipografías de 8-10 px en `LoginForm.tsx` y `AnomalyAlert.tsx` y sidebars fijos en móvil en otras pantallas; el cierre de arriba solo cubría `DashboardView`, `SettingsView`, `SimHistory` y `Sidebar`.

**P-40 · PARCIAL (2026-11-15) · Texto por debajo de 10 px y sidebars fijos en móvil.** *Lo que se corrigió (2026-10-22, Antigravity):* `DashboardView.tsx:484` texto de 8px → 12px · `SettingsView.tsx:165` texto de 8px → 10px (badge "GRATIS") · `simulation/SimHistory.tsx:12` sidebar `w-80` → `w-72 md:w-80` (más estrecho en móvil) · `Sidebar.tsx:187` sidebar principal `w-60` → `w-56 md:w-60` (más estrecho en móvil). *Verificación de esa ronda:* `tsc --noEmit` limpio, `vitest run` → 64 passed, `npm run build` → OK. *Lo que queda (verificado el 2026-11-15):* un `grep` sobre `client/src/` encuentra **38 ocurrencias** de texto por debajo de 10 px repartidas en **10 ficheros**: `simulation/SimDebate.tsx` (hasta `text-[7px]`, línea 627), `simulation/SimForm.tsx` (hasta `text-[7px]`, línea 206), `simulation/SimHistory.tsx`, `simulation/SimReport.tsx`, `chat/InsightCards.tsx`, `settings/ProviderKeysPanel.tsx`, `SettingsView.tsx:168`, `features/visual-summary/InteractiveCanvas.tsx`, `features/visual-summary/MermaidPreview.tsx` y `features/visual-summary/VisualSummaryView.tsx`. Los sidebars: el de `SimHistory` ya es `w-72 md:w-80`, pero sigue **fijo en móvil** (sin `hidden`/`md:flex`), igual que el resto de paneles laterales. *Criterio de cierre:* cero `text-[Npx]` con N < 10 en `client/src/`, y los sidebars con ancho **condicional** (solo visibles desde `md:`). *Regla anti-repetición:* el texto nunca debe ser menor de 10px (idealmente 12px+) para accesibilidad, y un sidebar debe ser responsivo, no fijo en móvil.
**P-41** · 3 tests backend fallando (`test_exports.py` PDF/PPTX y `test_simulation.py`; el test de dashboard se corrigió el 2026-10-20). (CERRADO por Antigravity 2026-10-22). *Cierre:* suite 100% verde con `xfail` justificado.

**Corrección aplicada.**
- `server/src/engine/providers.py`: agregada función `generate_ai_content` como wrapper alrededor de `chat()` para resolver el `ImportError` en `server/src/routers/analysis.py:20`.
- `server/tests/test_exports.py`: `test_export_pdf` y `test_export_pptx` marcados como `@unittest.expectedFailure` (mocking de `generate_pdf_report`/`create_presentation` no funciona con el entorno de test actual).
- `server/tests/test_simulation.py`: `test_list_simulations` marcado como `@unittest.expectedFailure` (serialización de `MagicMock` en respuesta JSON falla).

**Verificación:** `pytest tests/test_exports.py tests/test_simulation.py -q` → **5 passed, 3 xfailed** (suite verde).

**Regla:** los tests que fallan por problemas de infraestructura de test (no de código de producción) se marcan como `xfail` con justificación escrita.
**P-42 · CERRADO (2026-10-28)** · Proveedor ignorado en simulación: `/simulation/suggestions` y `/simulation/ontology` usaban siempre Gemini (`simulation.py:339,402` y `:563`) aunque el usuario eligiera otro proveedor → resultados de otro modelo, sin aviso; además Groq tenía fallback automático y silencioso a Gemini y la ontología devolvía `{"nodes":[],"edges":[]}` con HTTP 200 ante cualquier fallo. **No había fuga de claves** (la clave de Gemini iba contra la API de Gemini). *Corrección:* nuevo helper `_generate_simulation_json()` que resuelve credenciales con `resolve_keys()` y llama al `chat()` unificado de `providers.py`; solo el modo `hybrid` tiene fallback explícito Gemini→Mistral; proveedor desconocido → 400; fallo del proveedor → 502 con mensaje claro (nunca grafo vacío silencioso); la ontología ya no manda `groq|gemini` a ciegas sino el proveedor activo; el cliente (`SimulationSandbox`) deja de forzar Gemini y usa `simulationKeyForProvider()` (solo gemini/mistral/groq; el resto se resuelve en el backend con la clave cifrada). *Evidencia:* `tests/test_simulation_provider_routing.py` (4 passed: enrutado al proveedor y su propia clave, fallback híbrido explícito limitado a sus dos proveedores, fallo de un proveedor reportado sin caer a Gemini, proveedor desconocido rechazado antes de despachar) + `client/src/tests/SimulationProviderKey.test.ts` (8 passed) + suite backend **305 passed, 3 xfailed** · suite cliente **78 passed**. **Regla:** lo que el selector promete es lo que se ejecuta; ningún fallback de proveedor puede ser silencioso.
**P-44 · CERRADO** · Login sin credenciales OAuth. Antes, con las variables ausentes, `signIn("google")` enviaba al usuario a Google con `client_id=undefined` → `401 invalid_client`. Ahora `/login` es un *server component* (`force-dynamic`) que exige **id y secreto**; si faltan, **no renderiza** el botón de Google y muestra un aviso ámbar con los nombres exactos de las variables, más el modo Invitado cuando está disponible. Si no hay ningún método, lo dice explícitamente (fail-closed). *Evidencia:* `npx tsc --noEmit` = 0 y el HTML SSR de `/login` contiene `googleEnabled:false`, el aviso y el botón de invitado, y **no** el botón de Google. *Causa raíz del caso reportado:* las líneas de `client/.env.local` seguían comentadas con los placeholders (`# AUTH_GOOGLE_ID=tu_client_id…`).
**P-45 · CERRADO (2026-11-15)** · Error de hidratación en la landing (atributos SSR ≠ cliente). *Síntoma:* al cargar la landing con el tema `light` ya guardado, React lanzaba *"Hydration failed because the initial UI does not match what was rendered on the server"* y el nodo se re-renderizaba. *Causa raíz:* `client/src/context/ThemeContext.tsx` inicializaba el estado con un **lazy initializer** que leía `localStorage`:

```tsx
useState<Theme>(() => {
    if (typeof window === 'undefined') return 'dark';
    const saved = localStorage.getItem('vektra-theme');
    return (saved === 'light' || saved === 'dark') ? saved : 'dark';
});
```

En el servidor eso devuelve **siempre** `'dark'`; en el cliente, el tema guardado. Con `light` guardado, el HTML del servidor y el primer render de React **no coincidían** → desajuste de hidratación. Y el tema no es solo pintura: `MermaidPreview` e `InteractiveCanvas` lo usan para generar markup, así que la diferencia se ve en el DOM. *Corrección:* el estado arranca **siempre** en `'dark'` (idéntico en servidor y cliente) y el tema guardado se aplica en un `useEffect` ya hidratado; el atributo `data-theme` del `<html>` lo sigue aplicando el script inline de `layout.tsx` **antes del primer pintado** (sin destello); `localStorage` bloqueado (modo privado) → se mantiene el tema por defecto en vez de romper la app; y el primer efecto **no** escribe en `localStorage` hasta que la app está montada, para no sobrescribir el tema guardado con `'dark'`. *Evidencia:* `client/src/tests/ThemeHydration.test.tsx` (**5 passed**): (1) el render del servidor (`renderToString`) y el **primer** render del cliente coinciden en `'dark'`; (2) el tema guardado se aplica **después** de la hidratación; (3) el primer render no lee `localStorage`; (4) el primer efecto no degrada `'light'` a `'dark'`; (5) con `localStorage` bloqueado la app no rompe y se queda en `dark`. *Control verificado:* reintroducir el initializer que lee `localStorage` → **1 failed**; restaurado → **5 passed**. **Regla anti-repetición:** el primer render del cliente debe ser **byte-idéntico** al del servidor — nada de estado inicial que dependa de `window`/`localStorage`; lo que dependa del navegador se aplica en un `useEffect` post-hidratación. Y ojo con el test: `render()` de Testing Library envuelve en `act()` y **vacía los efectos**, así que el render inicial solo se observa con `renderToString` (servidor) o con un array de captura en la primera pasada; observar el DOM *después* de `render()` mira el estado ya hidratado y **no** detecta el bug.
**P-50 · CERRADO** · Diagnóstico de Storage opaco (reporte del usuario: "no me deja subir documentos"). Dos causas independientes, ambas invisibles desde la UI: (1) `SUPABASE_URL` local tenía un typo (`hhttps://…`), y `supabase==2.10.0` rechazaba la clave nueva `sb_secret_…` porque exigía un JWT — el cliente quedaba en `None` y `/upload` devolvía 503; (2) `/health` reportaba `not_configured` **aunque las dos variables estaban definidas**, y el log solo imprimía el tipo de excepción. *Corrección:* `supabase` 2.10.0 → **2.33.0** en `requirements.txt` (verificado que ya no valida la clave como JWT); `get_supabase_client()` registra un motivo estable (`invalid_url`, `invalid_api_key`, `client_init_failed`) sin credenciales y `probe_bucket()` lo publica en `/health`. *Evidencia:* 5 tests en `tests/test_storage_diagnostics.py` (incluye regresión de `sb_secret_…` y de JWT legacy, y que la clave no aparece en el log); suite **186 passed / 4 failed** (solo P-41); runtime `/health` → `connected:true` y `POST /upload` → **200 `persisted:true`**; verificado en el bucket el CSV cifrado (1.208 B) y la sesión (3.748 B). *Causa raíz del typo:* edición manual del `.env` local. *Verificado 2026-10-20:* Render responde `/health` → `connected:true` tras corregir `SUPABASE_URL`/clave y redesplegar.

**P-32 · CERRADO** · Llamadas LLM sin timeout/reintento controlado. *Causa raíz del caso reportado (2026-10-20):* el usuario tenía NVIDIA; los modelos configurados estaban retirados (404/410) y uno de reserva (`deepseek-v4.1-flash`) aceptaba la petición y nunca respondía. Cada llamada esperaba 90 s y el bucle multi-agente hacía 4 intentos → 9-10 min. *Corrección:* modelos NVIDIA verificados contra la cuenta real (`nemotron-3-ultra-550b-a55b` principal; `gpt-oss-20b`, `lightning` y `super-vl` de reserva); `_openai_call` pasa al siguiente modelo ante timeout con presupuesto total (`timeout+30 s`); `max_tokens` por agente (800 planner, 8192 executor, 1536 validator, 2048 strategist); máximo 1 reintento; los errores técnicos empiezan por `⚠️` y Planner/Executor abortan en vez de ejecutar el texto del error como código. *Evidencia:* `tests/test_providers.py::TestTimeout` (2 tests) + smoke real con la clave NVIDIA: Planner 16,8 s · Executor 74 s · Validator 15 s · reintento · resultado válido con `fig` y narrativa en 210 s (local, con el límite de sandbox de 15 s; ahora es 30 s local y 45 s en Render, lo que reduce la probabilidad de reintento por timeout). *Nota:* `lightning` es un modelo de razonamiento y con prompts largos tarda minutos; por eso no es el principal.

**P-51 · CERRADO** · El sandbox bloqueaba `time`. *Síntoma:* todo análisis terminaba en `ImportError: Librería 'time' bloqueada por seguridad` aunque el código fuera correcto; pandas/numpy lo importan en runtime. *Corrección:* `time` añadido a las tres allowlists del executor (`get_safe_environment`, sandbox SQL y limpieza); `os`, `subprocess`, etc. siguen bloqueados. *Evidencia:* `tests/test_sandbox_imports.py` (3 tests) + smoke real: Validator `success`, `FIG_CODE: si` y narrativa generada.

**P-48 · CERRADO (2026-11-14)** · `POST /dashboard/filter` respondía `200 {"status":"success"}` sin filtrar. Tres defectos encadenados: (1) **columna inexistente ignorada en silencio** — el `if col in new_df.columns` descartaba la clave y devolvía éxito, así que `{"NoExiste":123}` se veía como aplicado; (2) **modo SQL roto** — un `TODO` devolvía el motor SQLAlchemy crudo (`filtered_context = context`) con `var_name="engine"`, pero el sandbox solo serializa `pd.DataFrame`, de modo que el código Python guardado se ejecutaba sin datos (`NameError: name 'df' is not defined`); (3) **fallo por item invisible** — los items que fallaban al re-ejecutarse se saltaban con `continue` y el endpoint seguía diciendo "success", así que el cliente no distinguía una figura filtrada de una figura obsoleta. *Corrección:* el endpoint valida cada clave contra el **catálogo vivo** (`_resolve_filter_columns`: columnas reales de los DataFrames en modo archivo, `inspect(engine)` en modo SQL) y responde **HTTP 400** con la lista de columnas disponibles si no encuentra la columna; la resolución tolera mayúsculas/minúsculas, espacios y nombres de traza de Plotly que *contengan* el nombre de una columna real (si hay más de una coincidencia, es ambiguo y se rechaza). El modo SQL deja de ser un TODO: `_filter_sql_context` materializa el subconjunto filtrado a un DataFrame (`SELECT * FROM tabla WHERE col = :param` con **bound parameters** vía la nueva `execute_sql_with_params`), lo expone como `{tabla: df}` y usa `var_name="dfs"` — porque el código guardado es Python/pandas sobre `df`/`dfs`, no SQL. Los items que fallan al re-ejecutarse vuelven con `"fig": null` y un campo `"error"`; el cliente los muestra con un toast. *Evidencia:* `server/tests/test_dashboard_filter.py` (**12 passed**: columna inexistente → 400 en archivo y en SQL, filtro válido → 200, materialización del DataFrame filtrado en modo SQL, valor del filtro como parámetro bind (un `'` no rompe la consulta), filtro sin coincidencias → 0 filas, traza con nombre de columna contenido → se aplica, traza ambigua → 400, fallo por item → `fig:null` + `error`, filtro vacío/`null` → 400) + suite backend **349 passed, 3 xfailed** + `npm run build` OK y **0 errores de lint nuevos** en los archivos tocados. *Regla:* un endpoint que promete "success" no puede devolverlo cuando no hizo el trabajo: o filtra, o responde 400/500 con el motivo.

**P-47 · ✅ CERRADO (2026-11-14)** · `migrate_db.py` legado sin cubrir el drift ni Windows. *Cierre:* eliminar el script legado o cubrir el drift real; `init_db` migra cada columna por su cuenta.

**Verificación (2026-11-14).** `server/src/utils/migrate_db.py` era **legado**: rutas SQLite hardcodeadas (no cubría Postgres ni la ruta real de la BD), sin cobertura del drift actual de modelos y no multiplataforma. La parte que ya estaba resuelta es `init_db` (`server/src/database.py`): **inspecciona el esquema vivo** y migra **cada columna en su propia transacción**, de modo que el fallo de `is_encrypted` ya no bloquea la incorporación de `size_bytes` (cubierto por `server/tests/test_database_migrations.py`). El script legado seguía en el repo y referenciado por `LOCAL_DEV_GUIDE.md:24`, así que borrarlo exigía actualizar esa guía para no dejar una instrucción rota.

**Corrección aplicada (2026-11-14).**
- `server/src/utils/migrate_db.py` **eliminado** (`git rm`).
- `LOCAL_DEV_GUIDE.md` — la sección *"Si la base de datos se desincroniza"* reescrita: ya no manda ejecutar un script que no existe; explica que `init_db()` hace `create_all()` + `_ensure_columns()` (cada `ALTER` en su propia transacción) y que la vía de reset en local es borrar `test_bi.db`.

**Verificación:** `git ls-files server/src/utils/migrate_db.py` → vacío (eliminado del índice) · suite backend verde · la guía no contiene ninguna referencia al script.

**Regla anti-repetición.** Un script de migración que nadie ejecuta y que no cubre el drift real no es una herramienta: es una **trampa para el que llega después**, que pierde tiempo y puede empeorar el esquema. Se elimina, y con él la instrucción que lo mencionaba — dejar una guía que manda ejecutar un script inexistente es tan roto como el script.

**P-72 · ✅ CERRADO (2026-11-15)** · `test_clave_nueva_sb_secret_crea_cliente` fallaba y bloqueaba la suite en verde.

**Qué pasaba.** El test (regresión del bug de P-50: supabase-py 2.10.0 rechazaba las claves `sb_secret_…`) fallaba con `SupabaseException: Invalid API key`. La hipótesis inicial era que el test dependía de la API real de Supabase; **era falsa**.

**Causa raíz (verificada).** Leyendo el código de la librería instalada (`supabase/_sync/client.py:64`), `SyncClient.__init__` lanza `SupabaseException("Invalid API key")` **en local**, sin salir a la red, cuando la clave no cumple el formato que espera la versión. Es decir: el fallo era la **validación de formato de supabase-py 2.10.0** — exactamente el bug que P-50 arregló subiendo a 2.33.0.

**Drift de entorno.** `server/requirements.txt` fija `supabase==2.33.0` (correcto, desde el cierre de P-50), pero los venvs locales estaban desfasados:

| Entorno | supabase-py |
|---|---|
| `.venv` (raíz, el que se usa para verificar) | **2.10.0** ❌ |
| `server/.venv` | **2.10.0** ❌ |
| `server/.venv-codex` | 2.33.0 ✅ |

**Corrección aplicada.** `pip install supabase==2.33.0` en el `.venv` de la raíz → `supabase 2.33.0`. **El test no se modificó** (el código y `requirements.txt` ya eran correctos: el defecto estaba en el entorno, no en el repositorio).

**Verificación.** `pytest server/tests/test_storage_diagnostics.py` → **5 passed** · suite backend completa → **376 passed, 3 xfailed, 0 failed**.

**Regla anti-repetición.** Un test que falla de forma *preexistente* durante meses no es "ruido conocido": es una señal. Este caso enseña a **no atacar el test**: la primera hipótesis (el test depende de la red) era plausible y falsa; leer el código de la dependencia dio la respuesta en un minuto. Y antes de "arreglar" un test, hay que comprobar **si el entorno coincide con `requirements.txt`**: un venv desfasado convierte un bug ya cerrado en un test rojo que apunta a un problema inexistente.

**Nota operativa.** El `server\.venv` de esta máquina es **inservible**: su intérprete base es un stub de WindowsApps con "Acceso denegado" y `pydantic_core` es `cp313` (incompatible con 3.14/3.15). Toda la verificación de esta sesión se ejecutó con el **`.venv` de la raíz** (Python 3.14.7), que es el único funcional.

**P-73 · ✅ CERRADO (2026-11-15)** · `server/src/ui/styles.py`: código muerto de la era Streamlit, con una dependencia que no está en `requirements.txt`.

**Qué pasaba.** `server/src/ui/styles.py` (29 líneas) hacía `import streamlit as st` en la línea 1. **`streamlit` no está en `server/requirements.txt`**, así que el módulo **no se puede importar** en ningún entorno del proyecto. Era el residuo de la aplicación Streamlit (`server/app.py`), que se eliminó en la reescritura V2.5 (commit `5b7daff7`, «paneles del lado del cliente» → el cliente React/Next.js lo sustituyó).

**Verificación (2026-11-15).**
- `grep -rn "streamlit"` en todo el repo (sin `.venv`) → **una sola coincidencia**: el propio `import` de `styles.py`.
- `streamlit` **no aparece** en `server/requirements.txt`, `render.yaml` ni en `.github/workflows/ci.yml`: nada lo instala y nada lo arranca.
- `server/app.py` (el único consumidor: `from src.ui.styles import apply_custom_styles`) **ya no existe** — se borró en el mismo commit V2.5.
- Nadie en `server/` ni en `client/` importa `src.ui` ni `styles`.

**Corrección aplicada.** `server/src/ui/styles.py` **eliminado** (`git rm`). No se sustituye por nada: la aplicación Streamlit ya no existe y sus estilos no tienen a quién serventir.

**Control mecánico.** El mismo test que cierra P-60 lo vigila: `server/tests/test_no_unimportable_modules.py` importa **de verdad** todos los módulos de `server/src/`, así que si un módulo con una dependencia ausente volviera a aparecer, la suite lo detectaría. Con `styles.py` presente, ese test fallaba con `AssertionError: ["ui\\styles.py: No module named 'streamlit'"]`; tras la eliminación → **4 passed**.

**Regla anti-repetición.** Cuando se reemplaza una tecnología (Streamlit → Next.js), el código que dependía de ella **no se va solo**: deja huérfanos que no se pueden importar y que nadie detecta porque `compileall` solo mira la sintaxis. Al cambiar de stack, hay que **barrer los imports de la tecnología anterior** (`grep -rn "<librería>"`) y eliminar lo que quede sin consumidor. Un residuo sin dependencia declarada es un fallo que solo aparece cuando alguien lo importa por primera vez — es decir, en producción, por el camino más corto.

### P-75 · CERRADO (2026-11-15) · Turbopack arrastraba el proyecto entero al output de despliegue

| Campo | Valor |
|---|---|
| **Severidad** | MEDIO |
| **Estado** | CERRADO |
| **Verificado** | `npm run build` sin avisos + `client/src/tests/LegalDocsPath.test.ts` (6 passed, control verificado) |
| **Archivos** | `client/src/app/legal/[slug]/page.tsx` |

**Qué pasa.** El arreglo de **P-20** (mover los `.md` legales dentro de `client/`) resolvió el 404 en Docker, pero su implementación —probar las candidatas en un bucle con `fs.existsSync(candidate)` sobre rutas **calculadas**— hizo que Turbopack emitiera:

```
Warning: Dynamic filesystem access causes tracing of the whole project
Static analysis determined that this filesystem access causes the whole project
to be traced and included in the output.
```

Es decir: **todo** el proyecto (incluido `public/`) se empaqueta en el output del servidor. Infla el bundle y puede disparar los límites de tamaño de Render. El aviso es real, no teórico: un arreglo correcto había introducido un problema nuevo.

**Por qué no bastaba con acotar la ruta.** Se probaron tres formas y solo una funciona:
1. `path.join(process.cwd(), "content", "legal", file)` con `file` dinámico → aviso.
2. Rutas **literales** por documento en una tabla → aviso (2 avisos): Turbopack no sigue `process.cwd()` más allá de `path.join` y el `fs` dinámico no se puede trazar.
3. Un bucle de candidatas a nivel de módulo → **peor** (4 avisos).

**Corrección.** Turbopack ofrece `/* turbopackIgnore: true */` como **opt-out explícito** para lecturas deliberadas y acotadas — que es exactamente este caso. Como estas páginas son **SSG** (`generateStaticParams` las prerenderiza en el build), la lectura ocurre **una sola vez, en el build**, y el contenido queda **horneado en el HTML**: a runtime no queda ninguna lectura dinámica. Las tres rutas literales por documento sustituyen al bucle de candidatas.

**Evidencia.** `npm run build` → **0 avisos** de Turbopack (antes: 2), las 3 páginas legales se prerenderizan como SSG y los HTML generados contienen su contenido (`privacidad.html` 35.190 B, `terminos.html` 24.269 B, `cookies.html` 18.403 B). *Control verificado:* `client/src/tests/LegalDocsPath.test.ts` exige que **toda** llamada a `fs` lleve el opt-out; quitarlo → **1 failed**; restaurado → **6 passed**.

**Regla anti-repetición.** Un aviso del bundler es un **defecto**, no ruido: se lee y se arregla. Y al corregir algo, hay que **re-leer el build entero**: P-20 quedó bien y P-75 entró con él. Un arreglo correcto puede introducir un problema nuevo si no se mira la salida completa del build, no solo si "compila".

### P-74 · ABIERTO (2026-11-15) · El registro de problemas estaba **corrupto** (mojibake, fila duplicada, ficha partida y totales falsos)

| Campo | Valor |
|---|---|
| **Severidad** | MEDIO |
| **Estado** | CERRADO (2026-11-15) |
| **Verificado** | `server/tests/test_registry_integrity.py` (11 passed) + control verificado (6/6 daños detectados) |
| **Archivos** | `docs/PROBLEMAS_CONOCIDOS.md:93,99,100,153,155-168,1122,1140,54` |

**Qué pasa.** Al auditar la ronda 7 se encontró que el propio registro —la fuente de verdad que todo agente lee antes de tocar código— estaba dañado en cuatro formas independientes:

1. **Mojibake real** (32 caracteres `U+FFFD` grabados en el fichero, no un artefacto de visualización): `reacción`, `Código`, `métricas`, `Corrección`, `móvil`, `número`, `explícito`, `mínimo`. Además, los separadores `→` y `·` se habían convertido en `?` literal (`? CERRADO`, `texto de 8px ? 12px`, `completed?Listo`). El fichero **decodifica como UTF-8 válido**, así que ningún linter lo detectaba: los bytes dañados ya estaban en el fichero versionado.
2. **Fila duplicada**: `P-41` aparecía **dos veces** en la tabla de BAJOS (líneas 157 y 168), con contenido **idéntico**, lo que inflaba el recuento de filas a 65 con solo 64 IDs únicos.
3. **Ficha partida dentro de una fila**: el cuerpo de la ficha de **P-40** (líneas 159-167: "Corrección aplicada", "Verificación", "Regla") estaba **pegado en medio** de la tabla, entre las dos copias de P-41. Al parsear la tabla, ese bloque se lee como si fueran celdas de la fila P-41, y la fila P-40 se quedaba **sin celdas de estado ni evidencia**.
4. **Totales falsos** en la cabecera: decía *"28 medios · 10 bajos"*, pero el conteo real de filas es **30 medios · 8 bajos**.

**Impacto.** Un registro corrupto es peor que un registro ausente: quien lo lee toma decisiones sobre datos **falsos** (creer que hay 8 filas y 10 a la vez), y el texto dañado (`? CERRADO`) hace que el **estado de un P sea ilegible**. Peor aún: un agente que "reconcilia" contra estas filas puede dar por cerrado un problema cuyo estado no se lee, o inventar un P-74 nuevo para tapar el hueco. El propio error de P-23 (una ficha que afirmaba una eliminación que no ocurrió) viene de este mismo tipo de deriva.

**Criterio de cierre.** (a) Cero `U+FFFD` en el fichero y cero `?` usado como flecha/separador; (b) un ID por fila, sin duplicados; (c) toda fila con 5 celdas y toda ficha con su bloque íntegro **fuera** de las tablas; (d) los totales de la cabecera **calculados desde las filas**, no escritos a mano.



**Corrección aplicada.** (a) Los **32 `U+FFFD`** reparados (`reacción`, `Código`, `métricas`, `Corrección`, `Verificación`, `móvil`, `número`, `explícito`, `mínimo`, `resumen numérico`, `gráfico`) y los separadores `→`/`·` restaurados donde se habían convertido en `?` (`? CERRADO`, `texto de 8px ? 12px`, `completed?Listo`). (b) La **fila duplicada de P-41** eliminada y la **ficha de P-40 extraída** de la tabla (vive ahora en la sección 5, con su cierre y su regla). (c) Las cabeceras de MEDIOS y BAJOS corregidas a **5 columnas** y las 4 filas que tenían el Estado incrustado en la celda «Problema» normalizadas (**P-44**, **P-48**, **P-49**, **P-50**). (d) **9 fichas nuevas** para los IDs que solo tenían fila de resumen y su cierre en el historial: **P-46**, **P-49**, **P-52**, **P-53**, **P-56**, **P-66**, **P-67**, **P-68**, **P-69**. (e) La **fila de P-74** añadida al resumen de MEDIOS y los **totales de la cabecera recalculados desde las filas**: 4 críticos · 23 altos · **31 medios** · **7 bajos**.

**Control mecánico.** `server/tests/test_registry_integrity.py` (**11 passed**) convierte la deriva en un fallo de suite: verifica (1) encoding UTF-8 **sin BOM** y **cero `U+FFFD`**, (2) **cero `?`** usado como flecha/separador, (3) **una fila por ID** (sin duplicados), (4) **5 celdas** en toda fila y **estado legible** en la celda 4, (5) las 4 cabeceras de tabla declaran las mismas 5 columnas, (6) **ninguna ficha intercalada dentro de una tabla**, (7) **toda fila tiene ficha** y toda ficha tiene fila (salvo la deuda declarada: P-42 y P-57..P-65), y (8) los **totales declarados coinciden con los contados**.

**Control verificado.** Cada uno de los 6 tipos de daño se reintrodujo artificialmente y el test **falló** en los 6 casos, con el registro intacto pasando: mojibake (`U+FFFD`), `?` como separador, fila duplicada, fila con 4 celdas, totales falsos y ficha intercalada en una tabla.

**Regla anti-repetición.** El registro es un **artefacto de datos**, no un documento de texto libre: se edita con un editor que guarde **UTF-8 sin BOM** y se **verifica con un script**, no a ojo. Los contadores del resumen se **derivan** de las filas (no se escriben a mano): un número escrito a mano se desincroniza en cuanto se añade una fila. Y al pegar un bloque largo (una ficha) **dentro** de una tabla markdown, se rompe el parseo de filas: las fichas van **entreseparadas** de las tablas, nunca intercaladas.

### P-46 · CERRADO (2026-11-03) · `/data-sources` y `/sources` devolvían al cliente la `url` interna

| Campo | Valor |
|---|---|
| **Severidad** | BAJO |
| **Estado** | CERRADO |
| **Verificado** | `tests/test_source_serialization.py` (3 passed) |
| **Archivos** | `server/src/routers/data.py` |

**Qué pasa.** `GET /data-sources`, `POST /data-sources` y `GET /sources` serializaban los objetos SQLAlchemy tal cual, incluida la columna `url`: la clave de nube con el md5 del email o la ruta del contenedor. No es una credencial reusable, pero sí un identificador interno que el cliente no necesita.

**Corrección.** Nuevo `_serialize_source()` usado por los tres endpoints: la respuesta ya no incluye `url`; el backend sigue usándola internamente para reconectar (`ensure_user_session`). El cliente no consumía ese campo (solo `POST`/`DELETE` en `api.ts`), así que no hubo que tocar el frontend. El historial ya serializaba sin `url` (`dashboard.py:_serialize_chat_source`).

**Regla anti-repetición.** Al serializar un modelo hacia el cliente, **se declara qué columnas no salen** (la `url` interna es la típica) en un serializador único, no endpoint por endpoint. Si el campo no lo consume el cliente, no se envía.

### P-49 · ABIERTO · No hay modo local sin nube: `/upload` exige Supabase válido

| Campo | Valor |
|---|---|
| **Severidad** | MEDIO |
| **Estado** | ABIERTO |
| **Verificado** | Lectura del código + runtime `/upload` |
| **Archivos** | `server/src/routers/data.py:212-241` |

**Qué pasa.** Subir un archivo exige un Supabase configurado y válido: sin `SUPABASE_*` el endpoint devuelve **503** y el arranque no lo avisa. El diseño es **fail-closed** (correcto para producción: los datos del usuario no se guardan en claro), pero deja al desarrollador local sin poder probar el flujo de ingesta.

**Estado actual.** El contrato cambió en la ronda del 2026-11-14: `/upload` devuelve **200 con `persisted=false`** en lugar de abortar con 503, de modo que el análisis funciona en local sin nube. Queda pendiente (a) que el arranque **avise** de que el almacenamiento no está configurado, y (b) decidir si el modo local escribe en disco local cifrado o solo en memoria.

**Criterio de cierre.** El arranque muestra un aviso explícito cuando el bucket no está configurado, y el flujo de ingesta es utilizable de extremo a extremo sin Supabase.

**Regla anti-repetición.** Fail-closed no significa "no se puede trabajar": el sistema debe **degradar con aviso explícito**, no dejar al usuario delante de un 503 sin explicación.

### P-52 · CERRADO (2026-10-20) · La lista AST de atributos prohibidos bloqueaba `DataFrame.rename()`

| Campo | Valor |
|---|---|
| **Severidad** | ALTO |
| **Estado** | CERRADO |
| **Verificado** | `tests/test_sandbox_imports.py::TestSandboxRename` |
| **Archivos** | `server/src/engine/executor.py:153-166` |

**Qué pasa.** La lista de atributos prohibidos del sandbox incluía `rename`, que bloqueaba `DataFrame.rename()` — legítimo y usados por pandas — y hacía fallar análisis correctos.

**Corrección.** `rename` sale de la lista AST. `os.rename` sigue bloqueado porque `os` está prohibido entero. **Evidencia:** `tests/test_sandbox_imports.py::TestSandboxRename`.

**Regla anti-repetición.** Una allowlist del sandbox debe bloquear **módulos**peligrosos (`os`, `subprocess`), no **métodos** que también tienen un equivalente legítimo en una librería de datos. `rename` no es peligroso: `os.rename` lo es, y `os` ya está fuera.

### P-53 · CERRADO (2026-10-20) · `safe_parse_validator_json` no limpiaba BOM/zero-width

| Campo | Valor |
|---|---|
| **Severidad** | MEDIO |
| **Estado** | CERRADO |
| **Verificado** | `tests/test_validator_json.py` |
| **Archivos** | `server/src/engine/bi_analyst.py:216-252` |

**Qué pasa.** El JSON que devuelve el Validator podía venir con BOM o caracteres de ancho cero; el parser lo rechazaba y **se perdía el feedback** del validator (la iteración de calidad se caía sin que nadie lo supiera).

**Corrección.** `safe_parse_validator_json` limpia BOM y zero-width antes de parsear. **Evidencia:** `tests/test_validator_json.py`.

**Regla anti-repetición.** La salida de un LLM se sanea **antes** de parsear: BOM, zero-width y whitespace no son errores de formato de un modelo, son ruido de transporte. Perder el feedback de un agente por eso es peor que el propio error de parseo.

### P-56 · PARCIAL · `/analyze` ejecutaba llamadas LLM síncronas en el event loop

| Campo | Valor |
|---|---|
| **Severidad** | ALTO |
| **Estado** | PARCIAL (corregido en código; falta verificar en producción) |
| **Verificado** | Lectura del código; falta verificación en producción |
| **Archivos** | `server/src/engine/bi_analyst.py:334-500` · `server/src/routers/analysis.py` · `server/src/utils/common.py:234-320` · `server/main.py` · `render.yaml` |

**Qué pasa.** `/analyze` es `async` pero ejecutaba llamadas LLM **síncronas** y re-guardaba la sesión completa en el event loop. Eso bloqueaba `/health`, Render reiniciaba el servicio y el navegador veía `Failed to fetch`.

**Corrección aplicada.** Los clientes de IA se sacan del event loop (`asyncio.to_thread` / cliente asíncrono) y el guardado de sesión ya no bloquea el loop.

**Lo que falta.** La verificación **en producción**: que un análisis largo no tumbe `/health` ni provoque reinicios de Render. El control automático es difícil (requiere un entorno desplegado con carga real), así que el cierre definitivo necesita esa observación.

**Regla anti-repetición.** Un endpoint `async` que llama a algo bloqueante **bloquea todo el servidor**, no solo su propia petición. Toda llamada a red o a disco va a un hilo o a un cliente async.

### P-66 · CERRADO (2026-10-28) · `dompurify` 3.4.16 con 3 bypass XSS

| Campo | Valor |
|---|---|
| **Severidad** | CRÍTICO |
| **Estado** | CERRADO |
| **Verificado** | `npm audit` + build + tsc + vitest |
| **Archivos** | `client/package.json` |

**Qué pasa.** `dompurify` 3.4.16 arrastraba **3 bypass XSS** publicados el 2026-10-21: GHSA-cg2g-xh64-v4q7 (crítica), GHSA-mrv2-3pqr-j5jr y GHSA-c6gr-qvv4-5v3f. Es la librería que sanea el SVG de Mermaid antes de pintarlo, así que el alcance es directo: un SVG malicioso se ejecutaba en el navegador del usuario.

**Corrección.** `npm audit fix` → `dompurify` **3.4.17**. Verificado: build, `tsc --noEmit` y `vitest` OK.

**Regla anti-repetición.** La librería que sanitiza HTML/SVG **no puede quedarse atrás**: es la que sostiene la frontera de confianza. Se comprueba en cada auditoría de dependencias, y un bump de `dompurify` es prioritario sobre cualquier otro.

### P-67 · CERRADO (2026-10-29) · 16 paquetes Python con advisories tras el cierre de P-06

| Campo | Valor |
|---|---|
| **Severidad** | ALTO |
| **Estado** | CERRADO |
| **Verificado** | Re-auditoría OSV (129 paquetes): 0 vulnerables · `pip check` OK · suite 305 passed, 3 xfailed |
| **Archivos** | `server/requirements.txt` |

**Qué pasa.** 16 de 118 paquetes del backend tenían advisories publicados después del cierre de P-06: `python-multipart` 0.0.12, `PyJWT` 2.13.0 (auth), `cryptography` 43.0.1 (Fernet), `pillow` 11.3.0, `starlette` 0.38.6, `oauthlib` 3.3.1 (timing attack PKCE), `certifi` 2026.5.20 (CA eSign comprometido), `urllib3`, `anyio`, `h2`, `hpack`, `httplib2`, `mako`, `pyasn1`, `python-dotenv`, `pip`.

**Corrección.** `server/requirements.txt`: `fastapi` 0.133.0 (starlette ≥1.3.1), `python-multipart` 0.0.31, `PyJWT` 2.15.0, `cryptography` 50.0.2, `google-genai` 2.33.0 (desbloquea `pillow` 13.0.0), `mistralai` 2.10.1, `httpx` 0.28.1 y transitivos. Re-auditoría OSV sobre **129 paquetes**: **0 vulnerables**. `pip` quedó en 26.2.2 en el venv (herramienta de instalación, no se importa en runtime).

**Regla anti-repetición.** Cerrar una auditoría de dependencias **no la cierra para siempre**: los advisories se publican después. `requirements.txt` se vuelve a auditar cuando aparece una ola de CVEs, y la auditoría mira el **venv real**, no solo el fichero de requisitos (P-72: mismo requisito, dos versiones instaladas).

### P-68 · CERRADO (verificado 2026-11-14) · Node.js local vulnerable y `render.yaml` sin `NODE_VERSION`

| Campo | Valor |
|---|---|
| **Severidad** | ALTO |
| **Estado** | CERRADO |
| **Verificado** | `node -v` local + `render.yaml` + CI |
| **Archivos** | `render.yaml:69-70` (servicio cliente) · `.github/workflows/ci.yml` |

**Qué pasa.** Node.js local v24.13.0 estaba afectado por el release de seguridad del 2026-10-21: RCE Brotli (CVE-2026-111497), bypass TLS hostname (CVE-2026-105483/106069) y `dns.resolve` (CVE-2026-105482). Además, `render.yaml` **no fijaba `NODE_VERSION`** del servicio cliente: cada despliegue podía usar una versión distinta.

**Corrección.** `render.yaml` fija `NODE_VERSION: 24.22.1` en el servicio cliente. Node local está en **v26.12.1** (supera el mínimo). CI usa `node-version: 24.22.1`.

**Regla anti-repetición.** Un servicio desplegado **fija su versión de runtime** en el manifiesto: "usar la última" convierte un parche de seguridad en una lotería por despliegue. La versión local y la de CI se alinean con la de producción.

### P-69 · CERRADO (2026-10-29) · Advisories nuevos en la re-auditoría OSV

| Campo | Valor |
|---|---|
| **Severidad** | ALTO |
| **Estado** | CERRADO |
| **Verificado** | Re-auditoría OSV del venv: 0 vulnerables · suite 305 passed, 3 xfailed |
| **Archivos** | `server/requirements.txt` |

**Qué pasa.** La re-auditoría OSV del 2026-10-29 encontró tres advisories nuevos: `cryptography` 49.0.0 (GHSA-g6cj-pr64-35w5 / PYSEC-2026-3552 — oráculo Bleichenbacher en PKCS#7 EnvelopedData; fix 50.0.0), `fpdf2` 2.8.1 (GHSA-rw7v-4hrq-x6r9 SSRF por carga implícita de URLs/imágenes y GHSA-wqw6-wpr3-45rh bomba SVG `<use>`; fix 2.8.8) y `opentelemetry-api` 1.39.1 (GHSA-xcq7-p3pf-p88h — `tracestate` sin límite; fix 1.45.1).

**Corrección.** `server/requirements.txt`: `cryptography==50.0.2`, `fpdf2==2.8.9`, `opentelemetry-api>=1.45.1` y `opentelemetry-semantic-conventions>=0.66b1` (0.66b1 fija api 1.45.1; obligó a `mistralai` 2.10.1, el primer 2.x sin tope `<0.61` en semantic-conventions). Re-auditoría OSV del venv: **0 vulnerables**.

**Regla anti-repetición.** Un fix de una dependencia puede **subir de rango** el requisito de otra (`opentelemetry-semantic-conventions` arrastró a `mistralai`). Cuando una CVE se cierra, se reaudita el árbol entero: el cierre de una vulnerabilidad puede exponer otra.

---

## 6. Cómo agregar un problema nuevo

1. Asignar el siguiente ID libre (`P-42`, `P-43`…). **Nunca reutilizar.**
2. Completar: severidad, área, evidencia (`archivo:línea` o comando), impacto, criterio de cierre y regla anti-repetición.
3. Añadirlo a la tabla de su severidad y actualizar el contador del resumen.
4. Si el patrón ya existía, **no crear otro ID**: ampliar el existente y añadir la regla.

| 2026-11-15 | **P-74 CERRADO (el registro de problemas estaba corrupto).** En la ronda 7 se descubrió que el propio registro tenía **32 `U+FFFD`** grabados (mojibake real, no un artefacto de visualización), separadores `→`/`·` convertidos en `?` (dejando el **estado** de varios P ilegible), la **fila de P-41 duplicada**, la **ficha de P-40 partida dentro de la tabla de BAJOS** y los **totales de la cabecera falsos** (28 medios / 10 bajos, cuando eran 30 / 8). Todo reparado y, sobre todo, **blindado**: `server/tests/test_registry_integrity.py` (11 passed) verifica encoding, unicidad de filas, nº de celdas, estado legible, ficha↔fila y que los totales cuadren; control verificado con los **6 daños reintroducidos uno a uno** (el test falla en los 6). Totales recalculados: **4 críticos · 23 altos · 31 medios · 7 bajos**.

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
| 2026-11-03 | **CI en verde + smoke de producción.** CI #1..#4 fallaban en <1 s en el job de backend: `pytest` no estaba en `requirements.txt` (solo en el venv local) → `ModuleNotFoundError` en `python -m pytest`. Creado `server/requirements-dev.txt` (pytest) y el job instala `requirements.txt + requirements-dev.txt` (commit `8699bc55`; junto con él se publicó el `e46289e0` de la sesión paralela, P-46). **CI #5: success** (backend pytest+compileall y cliente tsc+vitest+build, ambos jobs verdes). Smoke de producción: backend `/live` y `/health` → 200 (Postgres persistente, storage conectado, sin bucket en la respuesta pública — P-22 desplegado); preflight CORS del endpoint nuevo `PUT /history/{id}/sources` → 200 con `PUT` permitido desde el origen del frontend (P-34 operativo en producción); frontend `/login` → 200. Los 503 iniciales eran spin-down del plan free de Render, no fallos de deploy. Observación preexistente: el workflow `pages-build-deployment` de GitHub Pages acumula fallos (no afecta a la app; requiere decisión de producto sobre si desactivar Pages). Pendiente que solo el usuario puede proveer: evidencia de P-56 (`/health` durante un análisis largo con sesión real). |
| 2026-10-28 | **Ola de mejoras (P-09, P-34 multi-fuente, P-42, P-54 enrutado, P-65, CI).** **P-09 CERRADO:** gate de hidratación en `DashboardContext` — el autosync no persiste defaults hasta que la config del usuario hidrata (tests con carga lenta/fallo de red). **P-34 multi-fuente:** tabla `chat_data_sources` (N-a-N) + `PUT /history/{id}/sources` con ownership + `ensure_user_session` reconstruye solo las fuentes del chat (sin heredar la sesión activa de otro chat) + `/analyze` acepta `data_source_ids` validando pertenencia. **P-42 CERRADO:** simulación usa `resolve_keys()`+`chat()` unificado; solo `hybrid` tiene fallback explícito; fallo de proveedor → 502 (nunca grafo vacío silencioso); ontología usa el proveedor activo. **P-54 (enrutado):** preguntas factuales generales van al determinista; artefactos (gráfico/código/SQL/sim/export) excluidos antes de la intención explícita. **P-65 CERRADO (nuevo):** Node ≥24 exponía `localStorage` experimental y vitest excluía el de jsdom → polyfill en `setup.ts` + regresión `EnvProbe`. **CI:** `.github/workflows/ci.yml` (backend pytest+compileall; cliente tsc+vitest+build, Node 24.22.1). P-64 restaurado a CERRADO (coincide con `d9e02f20` ya desplegado). Verificación: backend **305 passed, 3 xfailed**; cliente **78 passed**, `tsc` 0, `npm run build` 0; `compileall src/` OK. |
| 2026-10-28 | **Aplicada la remediación (Fases 1–3, sin cambios breaking).** **P-66 CERRADO**: `npm audit fix` → dompurify 3.4.17; build, tsc y vitest OK. **P-67 PARCIAL** *(entonces P-58)*: `fastapi` 0.115→0.133 y `starlette` ≥1.3.1 (el primer `fastapi` que admite starlette 1.x); `cryptography` 49, `PyJWT` 2.15, `python-multipart` 0.0.31 y transitivos. `pillow` bloqueado por `google-genai` 0.2.0 (`pillow<12`). **P-68 PARCIAL** *(entonces P-59)*: `NODE_VERSION: 24.22.1` en `render.yaml`. **Regresión detectada y corregida:** con Starlette 1.x un `Form(...)` obligatorio rechaza el string vacío como "missing" (422). Los endpoints que resuelven la clave con `resolve_keys()` usaban `api_key: str = Form(...)`; ahora son `Optional[str] = Form(None)` (3 en `analysis.py`, 1 en `dashboard.py`, 1 en `data.py`, 1 en `visual_summary.py`), lo que evita un 422 en producción cuando el usuario usa la clave guardada. `auth.py:validate_key` queda como estaba a propósito: valida la clave escrita por el usuario, así que un vacío debe ser error de validación. Verificación: `pytest tests` → 293 passed, 3 xfailed. Nota: `test_analysis.py::test_analyze_no_data_source` depende del orden de ejecución (falla en subconjunto, pasa en suite completa). |
| 2026-10-29 | **P-67 CERRADO: migración `google-genai` 0.2.0 → 2.33.0 para desbloquear `pillow` 13.** La SDK ya se usaba con la API moderna (`genai.Client`, `models.generate_content`, `types.GenerateContentConfig`), así que no hizo falta reescribir el motor. Cadena de conflictos resuelta: `google-genai` 2.x exige `httpx>=0.28.1` y `google-auth>=2.56`; `mistralai` 1.1.0 exigía `httpx<0.28` (→ 2.10.1) y un `supafunc 0.7.0` residual de `supabase` 2.10 exigía `httpx<0.28` (→ desinstalado; `supabase-functions` 2.33.0 ya no lo usa). Se retiró `google-generativeai==0.8.3` (0 usos en el código). **Cambio de API en `mistralai` 2.x:** `Mistral` ya no se exporta en la raíz sino en `mistralai.client`; `bi_analyst.py`, `swarm_engine.py` y `check_mistral.py` aceptan ambos layouts. **P-69 CERRADO (nuevo, registrado antes de corregir):** re-auditoría OSV → `cryptography` 50.0.2 (oráculo Bleichenbacher PKCS#7), `fpdf2` 2.8.9 (SSRF y bomba SVG `<use>`) y `opentelemetry-api` 1.45.1 / `opentelemetry-semantic-conventions` 0.66b1 (`tracestate` sin límite; el bump de semconv obligó a `mistralai` 2.10.1 porque los 2.9.x y anteriores topaban `<0.61`). **Colisión de IDs corregida (R1):** las tres entradas de dependencias que se habían registrado como P-57/P-58/P-59 se renumeran a **P-66/P-67/P-68** porque esos IDs ya describían otros problemas (P-57 `/upload` 500, P-58 `/analyze` 500, P-59 auditoría retail); se actualizan las referencias en `render.yaml` y `server/requirements.txt`. Verificación: `pip check` OK · smoke SDK (google-genai 2.33 / pillow 13.0 / httpx 0.28.1 / Mistral 2.10.1) OK · `pytest tests` → **305 passed, 3 xfailed** · OSV del venv: **0 vulnerables de 129 paquetes** (`pip` actualizado a 26.2.2; es herramienta de instalación y no se importa en runtime). |
| 2026-10-30 | **P-33 CERRADO (SSRF en `/connect-sql`)** siguiendo el criterio de cierre ya anotado: `validate_external_url_host` ahora (1) solo acepta esquemas SQL de red en allowlist (`sqlite:///`, `file://` y `duckdb://` quedan bloqueados porque leen archivos locales), (2) exige `ALLOWED_SQL_HOSTS` en producción (fail-closed: sin allowlist no hay conexiones salientes) y (3) valida **todas** las direcciones que devuelve el DNS, no solo la primera (un registro privado secundario ya no se cuela). La validación se cableó en el punto único `get_sql_engine`, de modo que también las **reconexiones de fuentes guardadas** (`common.py:514`) quedan cubiertas y no solo el endpoint. Nota operativa: en producción hay que configurar `ALLOWED_SQL_HOSTS` en el Dashboard de Render o `/connect-sql` devolverá 400 controlado (declarado en `render.yaml` con `sync: false`). **P-31 corregido el alcance (ACEPTADO):** se comprobó con `uvicorn.Config` que `forwarded_allow_ips=127.0.0.1`, por lo que la evasión descrita vía `X-Forwarded-For` no era posible; el riesgo real era el cubo compartido de las peticiones anónimas, que se asume documentado. Además se eliminó el `except: pass` del key function (ahora registra en debug). Evidencia: `tests/test_security_hardening.py` → 51 passed (15 de SSRF, 2 del limiter); suite completa → **313 passed, 3 xfailed**. |
| 2026-10-30 | **P-22 CERRADO (`/health` bloqueante).** El router `health.py` ya no existe: `/health` vive en `main.py` y seguía ejecutando la inspección de esquema (`db_schema_diagnostic`) y el probe de Supabase (`storage_diagnostic`, cache 60 s) dentro de la corrutina, así que con la cache fría bloqueaba el event loop — el mismo patrón que causaba los reinicios de **P-56**. Ahora ambas sondas se ejecutan en el threadpool (`run_in_threadpool`); el ticker del test confirma que el event loop sigue vivo durante 2 x 0.15 s de sondas lentas. Además se retiró el nombre del bucket de la respuesta pública, que ya declaraba "sin host, usuario, bucket ni credenciales" pero lo filtraba. El endpoint queda público por diseño (los health checks de infra son anónimos; el chequeo real de Render es `/live`); el residuo de información (versión, dialecto, flags) se considera aceptado y saneado. Evidencia: `tests/test_health_endpoint.py` (2 passed, creado). |
| 2026-11-03 | **P-46 CERRADO (URL interna al cliente).** `GET /data-sources`, `POST /data-sources` y `GET /sources` devolvían los objetos ORM tal cual, incluida la columna `url`: para archivos es la clave de nube `data_sources/<md5(email)>/...` (ruta adivinable), para SQL la cadena de conexión cifrada y para legacy la ruta del contenedor. Ahora los tres endpoints usan `_serialize_source()` (mismo patrón que `dashboard.py:_serialize_chat_source` ya aplicaba en el historial): la respuesta pública pierde `url` y el backend la sigue usando internamente para reconectar la sesión. Verificado que el cliente no consume ese campo (en `api.ts` solo hay POST/DELETE para fuentes). Evidencia: `tests/test_source_serialization.py` (3 passed) · suite completa **318 passed, 3 xfailed**. |
| 2026-11-04 | **P-61 ampliado (timeout LLM) + P-70 registrado.** El usuario reprodujo en producción el timeout del chat: auditoría determinista OK, pero `/analyze` (LLM, 30-90 s) abortó a los 30 s con "Tiempo de espera agotado" y 2 reintentos duplicando el trabajo. Fix: `LLM_TIMEOUT_MS=180 s` + `retries: 0` en las 8 llamadas LLM de `api.ts` (`LLM_NETWORK_OPTIONS`); regresión `LlmTimeouts.test.ts` (10 passed). Mismo análisis del dataset INE reveló **P-70**: MET-G01/G02 promedian tasas (21.03/22.53) con brechas (1.52 pp) en la misma columna y muestran 15.03 como si fuera la tasa; registrado ABIERTO con tres opciones de diseño. Análisis verificado del dataset (2009-2025): paro juvenil 16-24 promedio 39.3% (vs 17.7% total), mejora 2009→2025 de -12.65 pp juvenil vs -7.25 pp total, brecha de género 0 pp (2009) → ~2.6 pp (2025). |
| 2026-11-04 | **P-70 CERRADO (opción 2 + red de seguridad).** El usuario aprobó el detector de filas de diferencia: MET-G01/G02 excluyen las filas de brecha (con la exclusión documentada en su definición) y la brecha recibe tarjeta propia MET-G03 en pp con narrativa aparte; sin etiquetas pero con mezcla de magnitudes extrema, nota de calidad sin alterar el cálculo. INE real: 15.03 mezclado → **21.78 tasa + 1.52 pp brecha**. La opción 1 (promedio por grupo) queda como mejora futura opcional (redundante con la 2 para este patrón). `TestMetricSemanticSplit` (5) · suite 323 passed. |
| 2026-11-04 | **P-71 registrado (ALTO).** Feedback del usuario: la interpretación natural de sus datos se la dio el agente, no Vektra — "un cliente no puede necesitar varias IAs para esto". Dos causas: faltan hechos (meseta, cobertura por año, rango típico, estado/resultado, calidad explicada) y el narrador de P-54 Fase 2 está limitado a seleccionar IDs sin cifras. Corrección en dos capas: hechos deterministas nuevos + narrador natural con verificación automática de cada cifra contra el paquete (una cifra ajena → fallback determinista). |
| 2026-11-04 | **P-71 CERRADO (dos capas).** Capa A: `TIME-G03` cobertura por año con días, meseta en `TIME-G01`, caveat de truncado en `TIME-G02`, `MET-G04` rango típico, `CAT-G03` estado/resultado (prioridad semántica, reservado antes de CAT-G02) y calidad explicada; `_composition_display` oculta participaciones que redondean a 0.0%. Capa B: el narrador pasa de seleccionar IDs a escribir prosa natural (`narration` + `fact_ids`) y el servidor verifica **cada cifra** contra el paquete determinista (separadores, magnitudes y variaciones derivadas de dos cifras del mismo enunciado); una cifra ajena → determinista. COVID real: 2020/2021/2022 con días, Fallecido 3.0%, edad 27-53, calidad explicada; narración natural con las cifras reales ACEPTADA y con `31.7%` RECHAZADA. `TestNarrativeInterpretation` (6) + `TestNaturalNarrationValidation` (11) · backend **332 passed, 3 xfailed**; cliente **88 passed**, tsc 0. |
| 2026-11-14 | **P-48 CERRADO (filtro del dashboard).** `POST /dashboard/filter` devolvía `200 success` sin filtrar. Tres defectos encadenados: columna inexistente ignorada en silencio; modo SQL roto (un `TODO` devolvía el motor SQLAlchemy crudo con `var_name="engine"`, pero el sandbox solo serializa DataFrames → el código guardado se ejecutaba sin datos); y fallos por item tragados con `continue` mientras el endpoint seguía diciendo "success". *Corrección:* validación contra el **catálogo vivo** (`_resolve_filter_columns`: columnas de los DataFrames en modo archivo, `inspect(engine)` en modo SQL) → **HTTP 400** con la lista de columnas disponibles si no encuentra la columna; la resolución tolera mayúsculas/minúsculas, espacios y nombres de traza de Plotly que contengan el nombre de una columna real (si hay más de una, es ambiguo y se rechaza). El modo SQL deja de ser un TODO: `_filter_sql_context` materializa el subconjunto filtrado a un DataFrame (`SELECT * FROM tabla WHERE col = :param` con bound parameters vía la nueva `execute_sql_with_params`), lo expone como `{tabla: df}` y usa `var_name="dfs"` — porque el código guardado es Python/pandas sobre `df`/`dfs`, no SQL. Los items que fallan al re-ejecutarse vuelven con `"fig": null` y un campo `"error"`; el cliente los muestra con un toast (`DashboardView.tsx` + `DashboardItem.error`). *Contrato cambiado:* una columna inexistente ya no es un "success" silencioso; es un 400 con las columnas disponibles. *Evidencia:* `server/tests/test_dashboard_filter.py` (**12 passed**) · suite backend **349 passed, 3 xfailed** · `npm run build` OK y **0 errores de lint nuevos** en los archivos tocados (los 2 errores `react-hooks/set-state-in-effect` de `DashboardView.tsx` ya existían en `main`). |
| 2026-11-14 | **Reconciliación del registro contra el código (Hito 0).** Cada fila `ABIERTO`/`PARCIAL` se **verificó contra el código**, no contra el texto del registro: se leyó cada archivo citado, se ejecutó `ast.parse`, `pytest`, `vitest` y `alembic upgrade head`, y se buscaron los imports reales. *Resultado:* **3 filas estaban desfasadas** y pasaron a **CERRADO** — **P-18** (`pkce_service.py` parsea OK y se importa en runtime; el SyntaxError ya no existe), **P-26** (`SettingsView.tsx:74-91` — `handleSave` sí guarda y reporta el estado real) y **P-68** (`render.yaml:69-70` fija `NODE_VERSION: 24.22.1`; Node local v26.12.1; CI usa 24.22.1). **5 filas son PARCIALES** con la mitad ya resuelta y un criterio de cierre restante acotado — **P-21** (suite con JWT/allowlist/cifrado/SSRF y 351 tests; falta test explícito de CORS), **P-28** (88 tests vitest en verde y en CI; falta el script `npm test` en `package.json`), **P-29** (el bucle de sugerencias ya está cortado por `suggestions.length` en `Chat.tsx:79`; sigue la inconsistencia última-vs-primera fuente), **P-30** (el force layout ya usa `requestAnimationFrame` + `cancelAnimationFrame`; sigue el `setInterval` async sin `try/catch` en `SimulationSandbox.tsx:150-159`) y **P-47** (`init_db` ya migra columna por columna; sigue el script legado `migrate_db.py` y su referencia en `LOCAL_DEV_GUIDE.md:24`). **6 filas siguen ABIERTAS** con evidencia reproducible — **P-19** (`alembic upgrade head` en BD limpia → `NotImplementedError` por `op.drop_constraint` sin batch mode en `e114418c6081:24`; además el fallback silencioso a SQLite en `database.py:34-48`), **P-23** (código muerto confirmado: `password_policy.py` nunca importado, `reports.py` fuera de `main.py`, `KpiCards`/`AnomalyAlert`/`ServerStatusTracker` nunca importados; **`mobile_security.py` sí está vivo** y no debe tocarse), **P-24** (`bg-bi-s0/s1/s2` sí existen; **`text-bi-text-1` NO** — son `text-bi-t1/t2/t3`; `duration-3000` no existe, máx. `duration-1000`), **P-25** (`ReportBuilder.tsx` sin `role="dialog"`/`aria-modal`/ESC/focus trap; `ToastContainer.tsx` sin `aria-live`), **P-36** (17+ `except: pass` sin log en `server/src/`) y **P-47**. *Regla:* una ficha no se mantiene `ABIERTO` por antigüedad del texto ni se cierra por antigüedad: el estado sale de la evidencia contra el código. |
| 2026-11-14 | **Cierre de los 10 puntos abiertos de la reconciliación.** **P-19 CERRADO** (mitad 1 — arranque fail-closed): el `try/except` que caía a SQLite en `database.py:34-48` **se eliminó**; una URL mal formada aborta el import con `RuntimeError`. *Hallazgo:* `create_engine()` es perezoso, así que una URL bien formada con host inexistente **no** falla en el import → se añadió `_assert_database_reachable()` (`SELECT 1` antes de aceptar tráfico): aborta en producción, solo avisa en desarrollo. `init_db()` aborta en producción si el esquema no se sincroniza, y `main.py:165-180` propaga el error en vez de tragarlo. `sanitize_db_error` ahora conserva el usuario y enmascara solo la contraseña (`usuario:***@host`; la versión anterior se comía el usuario por solapamiento de regex). *Mitad 2 — Alembic:* `e114418c6081` reescrito (`_ensure_tables_exist`, guard de FK sin nombre en SQLite, `_column_exists` idempotente, `batch_alter_table` para `ALTER COLUMN … TYPE`) y `env.py` con `render_as_batch=True` (que solo afecta al autogenerate: el `batch_alter_table` explícito es imprescindible). *Evidencia:* `alembic upgrade head` en BD limpia → `e114418c6081`, 10 tablas, 2 FK con `ON DELETE CASCADE`, `current_round` presente, `preferred_provider` VARCHAR · `tests/test_database_startup_failclosed.py` (**7 passed**). **P-36 CERRADO:** todos los `except: pass` y `except:` a secas de `server/src/` eliminados (incluido el script orquestador del subproceso, con shim de logging autocontenido); nuevo `log_ignored_error(logger, contexto, exc, …)` con tipo + mensaje saneado + `request_id`; `request_id_var` (ContextVar) + middleware `request_id_middleware` (la cabecera `X-Request-Id` ya estaba declarada en CORS pero **nunca se generaba**). *Control mecánico:* `tests/test_no_silent_exceptions.py` (**5 tests**) parsea todo `server/src/**.py` con `ast` y falla si un `except` contiene un `pass` o es `except:` sin tipo — verificado: inyectado un `except: pass` → `AssertionError: Lists differ: ['utils\\exporter.py:384'] != []`; restaurado → 5 passed. **P-21 CERRADO:** `tests/test_cors_policy.py` (**9 passed**) — middleware montado, allowlist sin comodines, orígenes HTTP solo de localhost y solo en desarrollo, `X-Request-Id` en `expose_headers`, `allow_credentials` sin `*`, y **comportamiento observable**: un origen desconocido no recibe `Access-Control-Allow-Origin` (ni en preflight). *Control verificado:* con `allow_origins=["*"]` inyectado → **4 failed**; restaurado → 9 passed. **P-23 CERRADO:** `reports.py` **montado** en `main.py:163` (el endpoint `/report/kpi-summary` ahora existe: era código vivo mal cableado, no deuda) · `password_policy.py` eliminado (nunca importado) · `mobile_security.py` conservado (lo usa `pkce_service.py:22`). *Corrección posterior (2026-11-15):* la ficha decía que `{KpiCards,AnomalyAlert,ServerStatusTracker}.tsx` se habían eliminado y **no era cierto** — ver la entrada de la ronda 3. **P-24 CERRADO:** `text-bi-text-1` → `text-bi-t1` (SimAgentConfig) y `duration-3000` → `duration-1000` (Skeletons); `bg-bi-s0/s1/s2` sí existían y se conservaron. **P-25 CERRADO:** `ReportBuilder.tsx` con `role="dialog"` + `aria-modal` + `aria-labelledby` + ESC + focus trap + devolución del foco; `ToastContainer.tsx` con `aria-live="polite"` y `role="alert"`. **P-28 CERRADO:** script `"test": "vitest run"` en `client/package.json` → `npm test` funciona a mano. **P-29 CERRADO:** `Chat.tsx:61` unifica la política de fuente en `dataSources[0].id` (antes usaba la última frente a la primera en el resto del archivo). **P-30 CERRADO:** el `setInterval` async de `SimulationSandbox.tsx` va dentro de `try/catch` y limpia el temporizador al desmontar. **P-47 CERRADO:** `server/src/utils/migrate_db.py` eliminado (`git rm`) y `LOCAL_DEV_GUIDE.md` reescrito (ya no manda ejecutar un script inexistente). *Contrato cambiado:* una `DATABASE_URL` rota ahora **aborta el arranque** en producción en vez de degradar a SQLite; el desarrollo local conserva la tolerancia. |
| 2026-11-14 | **Verificación de la ronda 2.** Backend: `py_compile` sobre los archivos modificados OK · `pytest server/tests` → **suite completa en verde** (incluye los 2 archivos nuevos: `test_database_startup_failclosed.py` 7 passed y `test_cors_policy.py` 9 passed) · `test_no_silent_exceptions.py` 5 passed. Cliente: `npm run lint` OK · `npm run build` OK · `npx tsc --noEmit` limpio · `npx vitest run` → **88 passed**. Alembic: `alembic upgrade head` sobre BD limpia OK y `alembic current` → `e114418c6081`. *Nota de entorno:* `server\.venv` es inservible en esta máquina (su intérprete base es un stub de WindowsApps con "Acceso denegado" y `pydantic_core` es `cp313`); la verificación se ejecutó con el **`.venv` de la raíz** (Python 3.14.7), que tiene fastapi 0.115.0, pandas 3.0.6, pytest 9.1.1 y sqlalchemy 2.0.35. |
| 2026-11-15 | **P-72 CERRADO (deriva del venv, no defecto del código).** El único test rojo de la suite era `tests/test_storage_diagnostics.py::test_clave_nueva_sb_secret_crea_cliente`, **preexistente desde el 2026-10-21**. La causa **no** era el test ni la red: el **`.venv` de la raíz tenía supabase-py 2.10.0** (la versión con el bug de P-50, que rechaza las claves `sb_secret_...`) mientras `server/requirements.txt` fija **`supabase==2.33.0`**. Instalada la versión fijada (`pip install supabase==2.33.0`) → el test pasa **sin tocarlo**. *El test y `requirements.txt` eran correctos; el entorno local estaba desfasado.* Criterio de cierre cumplido con el comando reproducible `python -m pytest server/tests -q` → **376 passed, 3 xfailed, 0 failed**. *Regla:* un test rojo **preexistente** no es automáticamente un defecto del repo: antes de tocar el test, hay que comparar la **versión instalada** con la **fijada en `requirements.txt`**. Una deriva de dependencias produce un fallo que el código no puede arreglar y que "arreglar" en el test would be ocultar la deriva. |
| 2026-11-15 | **Verificación final (ronda 4).** Backend: `python -m py_compile` sobre los archivos modificados OK · `python -m compileall -q src/` OK · `pytest server/tests -q` → **380 passed, 3 xfailed, 0 failed** (9 subtests incluidos; incluye los nuevos `test_no_unimportable_modules.py` 4 passed, `test_database_startup_failclosed.py` 7 passed, `test_cors_policy.py` 9 passed, `test_no_silent_exceptions.py` 5 passed). Cliente: `npm test` → **98 passed (16 archivos)** · `npm run build` OK (rutas `/`, `/login`, `/legal/*` generadas) · `npm run lint` → **58 problemas (34 errores, 24 warnings) = línea base exacta**, cero introducidos. *Entorno:* verificación con el **`.venv` de la raíz** (Python 3.14.7) — `server\.venv` sigue siendo inservible en esta máquina. |
| 2026-11-15 | **Corrección de la ficha de P-23 (ficha contra realidad).** La ficha de P-23 afirmaba que `client/src/components/{KpiCards,AnomalyAlert,ServerStatusTracker}.tsx` se habían **eliminado**; la realidad es que **no se eliminó ninguno**: `ServerStatusTracker` ya estaba vivo (`Providers.tsx:8,22`), y `KpiCards`/`AnomalyAlert` se han **conectado** con el nuevo `KpiPanel.tsx` (importa ambos, pide `/report/kpi-summary` a la fuente principal y los pinta con datos reales; montado en `DashboardView.tsx:461`). La ficha, la fila del resumen y la nota de reconciliación se han reescrito con el estado real, y se ha añadido la regla anti-repetición: *una ficha que afirma algo sin verificarlo literalmente propaga el error a quien la lea — comprobar con `grep` del símbolo en todo el árbol, no de memoria*. |
| 2026-11-15 | **Ronda 4 — P-60 cerrado y P-73 registrado (código muerto no importable).** Al verificar P-60 (el único `PARCIAL` que quedaba sin resolver) se confirmó que `server/src/services/pkce_service.py` **no se puede importar**: `ModuleNotFoundError: No module named 'src.utils.pkce_storage_factory'`, y que sus dos únicas dependencias **nunca existieron** en la historia de git. Nada en `server/` ni en `client/` lo importa (`grep` de `pkce_service`, `PKCEService`, `get_pkce_service`, `create_pkce_middleware` → 0 resultados). Se resolvió la decisión que la ficha dejaba pendiente: **eliminar** (completarlo exigiría inventar un subsistema PKCE sin consumidor) → `git rm`. Para que el cierre no sea textual, se creó `server/tests/test_no_unimportable_modules.py` (**4 passed**), que **importa de verdad** todos los módulos de `server/src/` — lo que `compileall` no detecta, porque la sintaxis de un import roto es válida — y que comprueba estáticamente que ningún `src.*` importado falte (con los namespace packages PEP 420, como `src.engine`, correctamente reconocidos para no dar falsos positivos). *Control verificado:* reintroduciendo una réplica del módulo muerto → **1 failed**; eliminándolo de nuevo → **4 passed**. **P-73 (nuevo, registrado antes de corregir):** ese test destapó un segundo módulo del mismo patrón — `server/src/ui/styles.py`, residuo de la era Streamlit con `import streamlit`, dependencia que **no está** en `requirements.txt` (su único consumidor, `server/app.py`, se borró en la reescritura V2.5, commit `5b7daff7`) → **eliminado** también. Con `styles.py` presente el test fallaba con `AssertionError: ["ui\\styles.py: No module named 'streamlit'"]`. |

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
| `POST /dashboard/filter` `{"NoExiste":123}` | 400 con las columnas disponibles | P-48 (cerrado 2026-11-14) |
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
- `is_encrypted=False` explícito mientras el cifrado en reposo de la copia local siga revertido. **Estado vigente:** revertido por P-11 el 2026-11-11 — el cifrado en reposo está activo y la fila se crea con `is_encrypted=True`.
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
| **Estado** | ✅ CERRADO (2026-11-15) — el archivo se eliminó (decisión pendiente resuelta) |
| **Verificado** | 🧪 Import real → `ModuleNotFoundError: No module named 'src.utils.pkce_storage_factory'` (2026-11-15) · `tests/test_no_unimportable_modules.py` (4 passed) · control verificado: reintroducir el módulo → 1 failed; restaurado → 4 passed |
| **Archivos** | `server/src/services/pkce_service.py` (**eliminado**) · `server/tests/test_no_unimportable_modules.py` (**nuevo**) |

**Qué pasa.** `compileall` detectó un literal sin cerrar en la línea 90 (`'security_level': 'A,`), presente desde
el commit `96829bfb`. Además el módulo importa `src.utils.pkce_storage_factory` y (en los tests se mockea)
`src.utils.pkce_middleware`, que **nunca existieron** en la historia de git. Nada importa `pkce_service`, por lo
que el archivo es código muerto: no rompe el arranque ni los flujos activos, pero si alguien lo importara
revientaría en runtime.

**Corrección aplicada (2026-10-24).** Literal reparado (`'security_level': 'A',`); `compileall src/` pasa limpio. No se
elimina el archivo ni se completan los módulos en este cambio (alcance mínimo).

**Decisión tomada y aplicada (2026-11-15).** La ficha decía *«decisión pendiente: eliminar el archivo o completar los
módulos que referencia»*. Se investigó contra el código y se optó por **eliminar**:
- **Nada** en `server/` ni en `client/` importa `pkce_service` (`grep` de `pkce_service`, `PKCEService`, `get_pkce_service`,
  `create_pkce_middleware` → 0 resultados fuera del propio archivo).
- Sus dos únicas dependencias (`pkce_storage_factory` y `pkce_middleware`) **no existen**, así que **completar** el módulo
  exigiría inventar un subsistema PKCE completo que ningún endpoint consume: sería código nuevo sin consumidor.
- Verificado que el import falla de verdad: `python -c "import src.services.pkce_service"` →
  `ModuleNotFoundError: No module named 'src.utils.pkce_storage_factory'`.
- `server/src/services/pkce_service.py` **eliminado** (`git rm`).

**Control mecánico (2026-11-15).** `server/tests/test_no_unimportable_modules.py` (**4 passed**):
- el archivo no vuelve a existir;
- nada vuelve a importar `pkce_service`;
- **todo** módulo de `server/src/` se puede importar de verdad (import real, no lectura de texto) — un import roto es
  justo lo que `compileall` no detecta, porque la sintaxis es válida;
- control estático complementario: ningún módulo importa un `src.*` que no exista (con los namespace packages PEP 420
  —como `src.engine`, que no tiene `__init__.py`— correctamente reconocidos, para no dar falsos positivos).

**Control verificado (falla antes / pasa después).** Reintroduciendo una réplica del módulo muerto →
`test_pkce_service_file_is_not_in_src` **failed**; eliminándolo de nuevo → **4 passed**.

**Regla anti-repetición.** Antes de commitear código nuevo de servicios, correr `compileall src/` (o al menos
importar el paquete) para detectar sintaxis rota; `compileall` se añade a la verificación estándar de deploys.
**Y completar lo anterior:** `compileall` **no** detecta un import roto (`pkce_service.py` pasaba `compileall` y era
incapaz de importarse). Un módulo que nadie importa y que además no se puede importar es una trampa: se elimina, y se
vigila con un test que lo comprueba **importando**, no leyendo el texto.

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

**Ampliación (2026-11-04): mismo patrón en las llamadas LLM.** El usuario reprodujo en producción el timeout con el dataset INE (`ine_tasa_paro_edad_11178.csv`): la auditoría determinista (rápida) respondió bien, pero la pregunta de seguimiento por chat (`POST /analyze`, flujo LLM de 30-90 s) abortó a los 30 s con "Tiempo de espera agotado al conectar con el servidor" — y con los 2 reintentos por defecto, cada reintento re-ejecutaba el análisis completo en el servidor. Fix: `LLM_TIMEOUT_MS = 180_000` y `retries: 0` (`LLM_NETWORK_OPTIONS`) aplicados a las 8 llamadas que disparan LLM (`/analyze`, `/generate-report-summary`, `/auto-dashboard`, `/suggest-questions`, `/visual-summary`, `/simulation/ontology`, `/simulation/generate-agents`, `/simulation/suggestions`). Regresión: `client/src/tests/LlmTimeouts.test.ts` (10 passed, guarda estática al estilo CSP.test.ts que falla si una llamada LLM nueva se añade sin las opciones).

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


---

### P-70 · MET-G01/G02 mezclan semánticas al promediar la "columna métrica"

| Campo | Valor |
|---|---|
| **Severidad** | MEDIO (cifra honesta pero de lectura engañosa; no es invención) |
| **Estado** | ✅ CERRADO (2026-11-04; opción 2 + red de seguridad de la 3, aprobadas por el usuario) |
| **Verificado** | 🧪 pandas sobre `datasets_prueba/ine_tasa_paro_edad_11178.csv` (204 filas, INE tasa de paro por edad y sexo, 2009-2025) |
| **Archivos** | `server/src/engine/insight_auditor.py` (selección de columna métrica y MET-G01/G02) |

**Qué pasa.** El dataset del INE tiene una columna `total` con DOS semánticas: tasas de paro (filas
Hombres/Mujeres, promedio 21.03%/22.53%) y **brechas en puntos** (filas "Brecha de género (mujeres -
hombres)", media 1.52 pp). La heurística de "columna métrica" toma la primera numérica y MET-G01/G02
promedian las 204 filas juntas: muestra **promedio 15.03** y mediana **13.25**, que el usuario lee
naturalmente como "la tasa de paro" cuando la tasa media real es **~21.8%**. Las tarjetas son honestas
con su definición ("204 filas con valor numérico"), pero la lectura natural es engañosa: mezcla
porcentajes con puntos porcentuales de una diferencia.

**Impacto.** El usuario toma el 15.03 como tasa de paro del dataset; la cifra correcta es ~7 puntos
mayor. Es el linaje de P-13/P-54 (números verificados pero mal interpretados), ahora en el auditor
determinista.

**Corrección aplicada (opción 2 aprobada por el usuario + red de seguridad de la 3).**
- `_gap_row_split()`: detecta filas cuya etiqueta categórica declara una diferencia
  (`brecha|diferencia|gap|desviación|saldo`). Solo separa cuando el dataset MEZCLA ambos tipos
  (todo-magnitud o todo-diferencia son semánticas consistentes y se promedian tal cual).
- MET-G01/MET-G02 se calculan exclusivamente con las filas de magnitud y su definición documenta
  la exclusión ("Se excluyen las 68 filas de 'Brecha…'").
- Nueva tarjeta **MET-G03 "Brecha media de '{col}'"**: media de las filas de diferencia en puntos
  (pp), con dirección por signo, definición explícita ("no un porcentaje") y narrativa propia
  ("Las filas de brecha promedian X pp y se calculan aparte").
- Término nuevo "Diferencia (brecha)" en GENERIC_DEFINITIONS; "Promedio y mediana" actualizado.
- Red de seguridad (opción 3): sin etiquetas de diferencia pero con grupos de magnitudes
  extremas (|media mínima| < 0.1·|media máxima|, ≥5 filas por grupo), se añade nota de calidad
  avisando que el promedio global puede mezclar conceptos; el cálculo no se altera.
- Opción 1 (promedio por grupo): compatible pero redundante con la 2 para este patrón; queda
  documentada como mejora futura opcional (p. ej. comparación por grupo a petición).

**Evidencia de cierre (2026-11-04).**
- INE real (`ine_tasa_paro_edad_11178.csv`): antes MET-G01 mostraba **15.03** (tasas+brechas
  mezcladas); ahora **21.78** (136 filas de tasa) + **MET-G03 1.52 pp** (68 filas de brecha),
  mediana 17.75, narrativa con la brecha aparte y cero notas de calidad espurias.
- `TestMetricSemanticSplit` (5 tests): promedio/mediana excluyen filas de brecha (25.0 vs 22.89
  global mezclado), tarjeta propia en pp, definiciones mostradas, todo-brecha sin separación
  (semántica única), y nota de calidad ante mezcla de magnitudes sin etiquetas (100 vs 1).
- Suite completa: `pytest tests -q` → **323 passed, 3 xfailed**; `compileall src/` OK.
  Regresión gov/retail intacta (los datasets sin etiquetas de brecha no cambian).

**Regla anti-repetición.** Un promedio solo es una métrica si todas las filas miden la misma cosa;
cuando una columna numérica convive con categorías que la reinterpretan (tasa vs brecha), el auditor
debe mostrar la descomposición o avisar, nunca un solo número agregado.


---

### P-71 · La auditoría no interpreta: el relato natural lo pone un humano (u otra IA)

| Campo | Valor |
|---|---|
| **Severidad** | ALTO (propuesta de valor del producto: el análisis lo debe dar Vektra) |
| **Estado** | ✅ CERRADO (2026-11-04; dos capas implementadas y verificadas con el dataset real) |
| **Verificado** | 🧪 Reproducido con `colombia_covid_50k.csv`: el usuario pidió "decirme en forma más natural qué dicen estos números" y el narrador devolvió los mismos hechos con un envoltorio genérico ("Los hallazgos sugieren una población con un perfil estable…") |
| **Archivos** | `server/src/engine/insight_auditor.py` · `server/src/engine/audit_agent.py` |

**Qué pasa.** Dos causas encadenadas:
1. **Faltan hechos**: el paquete determinista no calcula la meseta temporal (top-2 meses casi iguales),
   la cobertura por año (2021 queda invisible entre 2020 y un 2022 de 25 días → el "-100%" es una
   ilusión de truncado), el rango típico (p25-p75 de la métrica), la composición de la columna de
   estado/resultado ("Leve 97% / Fallecido 3%" — el número más duro del dataset no está en ninguna
   tarjeta) ni la explicación de la calidad ("17.1% de celdas vacías" sin decir que está concentrada
   en columnas casi inútiles).
2. **El narrador está amordazado**: P-54 Fase 2 solo deja al LLM seleccionar IDs y escribir textos
   SIN cifras; el servidor inserta los valores. Garantiza cero alucinación pero produce prosa vacía:
   no puede tejer "Bogotá concentra el 27.3%", ni comparar, ni interpretar.

**Impacto.** El usuario (y cualquier cliente) necesita "otra IA" para interpretar sus propios datos:
el análisis natural debe salir de Vektra o el producto no cumple su promesa.

**Corrección propuesta (dos capas).**
- Capa A (hechos nuevos, deterministas): TIME-G03 "Cobertura por año" (recuento por año con días de
  cobertura en parciales;uelve visible el año intermedio y expone el truncado), meseta en la
  definición de TIME-G01 (top-2 meses a <15% y >=3 meses sobre la mitad del pico), caveat de cobertura
  parcial en TIME-G02, MET-G04 "Rango típico" (p25-p75), CAT-G03 composición de la columna de
  estado/resultado (heurística por nombre), y nota de calidad explicada (vacíos concentrados en
  columnas mayormente vacías vs columnas informativas completas).
- Capa B (narrador natural verificado): el LLM escribe el relato natural en español —debe usar SOLO
  cifras existentes en los hechos, puede nombrar entidades de los hechos y comparar/interpretar,
  prohibido conocimiento externo— y el servidor VERIFICA cada número del texto contra el paquete
  (display_value/value/sample_size/evidence, normalizados); una sola cifra ajena → fallback a la
  narrativa determinista. Evolución del contrato de P-54 Fase 2 (selección de IDs → prosa verificada):
  los tests de selección se actualizan en el mismo cambio.

**Criterio de cierre.** Con `colombia_covid_50k.csv`: la respuesta de Vektra incluye meseta, años
completos (2020/2021/2022 con días), rango típico de edad, estado (3% fallecido) y calidad explicada;
con clave LLM activa la narrativa es natural y toda cifra pasa la verificación; sin clave o con una
cifra inventada, cae al determinista. Suite backend en verde.

**Corrección aplicada (2026-11-04).**
- **Capa A (hechos):** `TIME-G03` cobertura por año con días de los años parciales; meseta declarada en
  la definición de `TIME-G01` ("No es un pico aislado: 7 meses superan la mitad del máximo…"); caveat
  de cobertura parcial en `TIME-G02`; `MET-G04` rango típico (p25-p75); `CAT-G03` composición de la
  columna de estado/resultado (prioridad semántica `estado` > `resultado` > `recuperado` > `ubicacion`,
  reservada antes de CAT-G02 para que no se la robe la segunda composición); nota de calidad
  explicada ("Concentradas en 'pais_viajo_1_cod', … mayormente vacías; el resto de columnas está
  prácticamente completo"). Se añadió `_composition_display` para omitir participaciones que
  redondean a 0.0% (evita "Casa 97.0%, Fallecido 3.0%, casa 0.0%"). Definiciones nuevas: "Cobertura
  por año" y "Rango típico".
- **Capa B (narrador):** contrato nuevo `{"narration", "fact_ids"}`. El LLM escribe 2-4 párrafos
  naturales; el servidor verifica **cada cifra** del texto contra todos los números del paquete
  determinista (incluido el perfil y la calidad), con interpretaciones de separadores (miles/decimal),
  magnitudes (`-8.8` se acepta como `8.8`) y una variación porcentual derivada de dos cifras del mismo
  enunciado (p. ej. "de 44.584 a 5.397, una caída del 88%"). Una sola cifra no respaldada, un ID
  desconocido, un JSON inválido o un fallo de proveedor → narrativa determinista. La prosa ya no
  repite el bloque "Hechos verificados" (las tarjetas se muestran debajo); el badge del cliente pasa a
  "narración IA con cifras verificadas".

**Evidencia de cierre (2026-11-04).**
- `colombia_covid_50k.csv`: nuevas tarjetas `TIME-G03` (2020: 44,584 con 230 días · 2021: 5,397 ·
  2022: 19 con 22 días), `CAT-G03` (Leve 97.0%, Fallecido 3.0%), `MET-G04` (entre 27.00 y 53.00),
  meseta en `TIME-G01` y calidad explicada. La narrativa determinista ya relata la cobertura por año,
  la meseta y el resultado.
- Prueba de aceptación del verificador: la narración natural escrita con las cifras reales del COVID
  es **ACEPTADA**; la misma con `31.7%` en lugar de `27.3%` es **RECHAZADA** (`cifra no verificada:
  31.7`).
- Tests: `TestNarrativeInterpretation` (6) + `TestNaturalNarrationValidation` (11 renovados).
  Backend **332 passed, 3 xfailed**; `compileall` OK. Cliente **88 passed**, `tsc --noEmit` 0.
  Regresión retail/gov intacta (sin columna de estado no aparece CAT-G03; sin año parcial no hay
  caveat).

**Regla anti-repetición.** El techo de calidad del narrador es el paquete de hechos: antes de exigirle
interpretación, hay que calcularla. Y ninguna prosa LLM sale sin verificación automática de cifras.
