---
name: vektra-claude-protocol
description: Protocolo operativo para Claude Code en el repositorio Vektra BI (Agente-BI). Úsalo al INICIAR cualquier tarea en este repo y también cuando Claude Code no encuentre las skills del proyecto. Fija el orden obligatorio de lectura (problemas conocidos → protocolo de interacción → skill de dominio), las reglas innegociables de AI_RULES.md, el mapa real de rutas del backend FastAPI y el frontend Next.js, los invariantes de seguridad de datos (upload cifrado, sandbox LLM) y la checklist de verificación antes de declarar terminada una tarea.
---

# Protocolo Claude Code — Vektra BI (Agente-BI)

Este archivo es el **puente entre Claude Code y las skills del proyecto**. Las skills
originales viven en `.codex/skills/` (convención Codex/Antigravity) y se referencian
desde `AGENTS.md`; Claude Code sólo lee `.claude/skills/`. Sincronízalas con:

```powershell
.\scripts\sincronizar-skills-codex-claude.ps1
```

## 1. Orden obligatorio (no lo alteres)

1. **`docs/PROBLEMAS_CONOCIDOS.md`** — léelo PRIMERO, siempre. El registro manda:
   si un problema ya está documentado, no lo re-investigues ni lo "re-descubras".
   Verifica el estado vigente (REABIERTO / RESUELTO) antes de tocar nada.
2. **`.claude/skills/user-interaction-protocol/SKILL.md`** — estructura la petición y
   fija los criterios de aceptación (regla obligatoria de `AI_RULES.md` #4).
3. **Una skill de dominio** según la tarea (§3). Si aplica más de una, la más específica gana.
4. **`.claude/skills/vektra-code-verification/SKILL.md`** — antes de decir "listo" (§5).

> Si el usuario pide una auditoría de plan, añade `vektra-critical-audit` ANTES de la de dominio.

## 2. Reglas innegociables (`AI_RULES.md`)

| # | Regla | Consecuencia práctica |
|---|-------|------------------------|
| 1 | **Gemini solo la whitelist vigente** (verificada 2026-11-11) | Ya NO es "familia 3.x intocable". Permitidos: `gemini-4-argon`, `gemini-4-carbon`, `gemini-3.8-flash`, `gemini-3.6-flash` (default), `gemini-3.5-flash-lite`, `gemini-3.1-pro-preview`. Prohibidos: `gemini-2.0-flash` (apagado 2026-06-01), `gemini-2.5-flash`/`2.5-pro` (redirigen 2026-12-01), `gemini-3-flash-preview` (obsoleto), `gemini-3.7-flash` y `3.5-flash` (redirigen). **Todos los strings viven en `server/src/engine/model_catalog.py`** (fuente única). Detalle, tabla de fechas y procedimiento de migración → skill `vektra-gemini-model-lifecycle`. |
| 2 | **Clientes de IA fuera del event loop** | NUNCA llames `.models.list()` / `.models.generate_content()` dentro de `async def` de FastAPI. Envuélvelo en `def` normal (FastAPI lo manda al threadpool) o usa `client.aio.*` / `run_in_threadpool`. Si no: `CANNOT SEND A REQUEST, AS THE CLIENT HAS BEEN CLOSED`. |
| 3 | **Validador de llaves flexible** | Un 429 / quota / limit significa que la llave ES VÁLIDA: guárdala y deja que el usuario pruebe otro proveedor (Mistral, etc.). No bloquees la UI con errores rígidos. Un 401/403 sí es llave rechazada. |
| 4 | **Cargar el protocolo de interacción** | Obligatorio en el primer turno y ante cada requerimiento nuevo (ver §1). Leer también `docs/PROBLEMAS_CONOCIDOS.md` antes de planificar o modificar. |
| 5 | **Verificar antes de declarar terminado** | `py_compile` + `pytest server\tests -q` + `npm run lint` + `npm run build`. Si no se pudo ejecutar, dilo explícitamente. |

## 3. Mapa de rutas (verifica antes de asumir)

**Backend — `server/`** (FastAPI 0.133, Python, SQLAlchemy 2.0, Alembic, pandas, matplotlib)

| Ruta | Qué hay |
|------|---------|
| `server/src/routers/data.py` | Upload de CSV/Excel, fuentes de datos, persistencia, cifrado en escritura |
| `server/src/engine/executor.py` | Ejecución del código Python generado por el LLM (sandbox) |
| `server/src/engine/prompts/agents.py` | Prompts del motor de análisis |
| `server/src/utils/common.py` | `load_source_to_session` (descifra si `is_encrypted=True`) |
| `server/src/connectors/data_connectors.py` | `load_file_data_from_bytes`, `ArchivoInvalido` |
| `server/src/utils/security.py` | `encrypt_file_to_bytes` / `decrypt_file_to_bytes` |
| `server/src/engine/bi_analyst.py` | Clientes Gemini/Mistral, `MODELS`, validador de llaves, reintentos 429 |
| `server/src/engine/providers.py` | Catálogo `PROVIDERS` (modelo + validación de llaves por proveedor) |
| `server/src/engine/swarm_engine.py` | Motor multi-agente (duplica strings de modelo — slated to migrar al catálogo) |
| `server/src/engine/model_catalog.py` | **Fuente única** de identificadores de modelo + fecha de verificación (a crear) |
| `server/migrations/` | Migraciones Alembic (`server/alembic.ini`) |
| `server/tests/` | Pytest (`test_data.py`, `test_engine.py`, `test_auth*.py`, …) |

**Frontend — `client/`** (Next.js + React + TypeScript + Tailwind + Zustand)

| Ruta | Qué hay |
|------|---------|
| `client/src/lib/api.ts` | Cliente HTTP: contratos, auth token, llamadas a analysis/dashboard |
| `client/src/components/Chat.tsx` | Chat del analista IA |
| `client/src/auth.ts` | Autenticación / sesión |

**Documentación clave** — `docs/PROBLEMAS_CONOCIDOS.md`, `docs/GUIA_AGENTE_REFERENCIA_RAPIDA.md`,
`docs/MANUAL_PRUEBAS_AJUSTES.md`, `docs/BITACORA_2026-11-07_AUDITORIA_Y_VISION_VEKTRA.md`,
`PLAN_P11_UPLOAD_SEGURO.md` (raíz), `AI_RULES.md`, `AGENTS.md`.

## 4. Routing de skills de dominio

| Tipo de tarea | Skill |
|---------------|-------|
| Frontend, dashboards, chat, UI | `vektra-product-design`, `vektra-frontend-state-management`, `universal-premium-web-design` |
| API / contratos cliente-servidor | `vektra-api-contracts` |
| Middleware, CORS, rate limit, red | `vektra-api-security`, `vektra-security-review` |
| Uploads CSV/Excel, Google Sheets, fuentes | `vektra-data-ingestion` |
| Explicaciones de negocio sobre datos | `vektra-data-semantics` |
| Alembic / modelos SQLAlchemy | `vektra-database-migrations` |
| Refactor grande, routers, workers | `vektra-architecture-refactor` |
| Sandbox / código generado por IA | `vektra-llm-sandbox-hardening` |
| Export PDF / PowerPoint | `vektra-exports-design` |
| Android / Compose | `android-material3-compose`, `android-architecture-mvvm`, `android-mobile-hardening` |
| Tests / mocks | `universal-api-mocking-and-testing` |
| CI/CD, despliegue VPS | `deployment-and-ci-cd-pipelines` |
| Modelos de IA, whitelist, deprecaciones, migración | `vektra-gemini-model-lifecycle` |

## 5. Checklist antes de declarar "terminado"

```powershell
# Backend (desde la raíz del repo)
server\.venv\Scripts\python.exe -m py_compile server\src\routers\data.py   # archivos modificados
server\.venv\Scripts\python.exe -m pytest server\tests -q                  # suite afectada

# Frontend
cd client; npm run lint; npm run build
```

Además, verifica estos escenarios (de `vektra-code-verification`):

- **NaN / inf**: el motor de análisis no debe crashear ni devolver `(nan)` al usuario.
- **Llave rotada**: si `decrypt_key` falla → **HTTP 400 limpio**, nunca claves corruptas hacia Gemini/Mistral.
- **Timeout de red**: el hilo del sandbox debe cortar la ejecución a los **10 s**.
- **Sin regresiones circulares**: nada de `UnboundLocalError` por variables/imports sombreados al levantar FastAPI.

## 6. Invariantes de datos (P-11, upload seguro)

En `server/src/routers/data.py:upload_file` el orden correcto es:

1. Leer bytes crudos (`file.file.seek(0)` → `raw_bytes`).
2. **`_reject_zip_bomb_early(raw_bytes, clean_name)` ANTES de parsear.**
3. Parsear en memoria (`load_file_data_from_bytes`).
4. **Cifrar en memoria antes de escribir**: disco y nube reciben bytes cifrados.
5. Persistir con `is_encrypted=True` (el read-back ya soporta cifrado en `common.py`).

Nunca escribas el original en claro en `.tmp`, en `data_sources/` ni en la nube.
Si tocas este flujo, revisa `docs/PROBLEMAS_CONOCIDOS.md` (P-11 y P-21) antes y después.

## 7. Anti-patrones (no los hagas)

- Usar un modelo fuera de la whitelist vigente (`gemini-2.0-flash` apagado, `gemini-2.5-*` redirigiendo) → viola la regla #1.
- "Bajar a 2.x porque 3.x falla" → al revés: 2.x está apagado o redirige; el problema es otro.
- Duplicar un string de modelo en un archivo que no sea `model_catalog.py` → viola la regla #1.
- Llamar al cliente de Gemini desde un `async def` → viola la regla #2.
- Bloquear la UI cuando una llave da 429 → viola la regla #3.
- Dar por bueno un cambio sin `py_compile` + tests → viola la regla #5.
- Re-descubrir un problema ya listado en `docs/PROBLEMAS_CONOCIDOS.md`.
- Tocar `.codex/skills/` sin volver a sincronizar `.claude/skills/`.
