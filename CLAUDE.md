# CLAUDE.md — Vektra BI (Agente-BI)

> Repo de un agente de BI: backend **FastAPI** (`server/`) + frontend **Next.js** (`client/`),
> con ingesta de datos, ejecución de código generado por LLM y exportación a PDF/PPT.

## Carga obligatoria

- `@AI_RULES.md` — reglas innegociables (whitelist de modelos Gemini vigente, clientes de IA
  fuera del event loop, validador de llaves flexible, protocolo de interacción, verificación
  obligatoria antes de cerrar).
- Lee **`docs/PROBLEMAS_CONOCIDOS.md`** antes de cualquier tarea (regla "problemas conocidos
  primero"). No re-descubras problemas ya registrados.

## Skills de este proyecto

Las skills viven en **`.claude/skills/`** (Claude Code) y se mantienen en **`.codex/skills/`**
(Codex/Antigravity). Si editas o creas una skill en `.codex/skills/`, sincroniza:

```powershell
.\scripts\sincronizar-skills-codex-claude.ps1
```

| Tarea | Skill |
|-------|-------|
| Cualquier tarea (protocolo, rutas, reglas, verificación) | `vektra-claude-protocol` |
| Problemas conocidos (siempre, primero) | `known-issues-registry` |
| Estructurar el requerimiento / criterios de aceptación | `user-interaction-protocol` |
| Frontend, dashboards, chat, UI | `vektra-product-design`, `vektra-frontend-state-management`, `universal-premium-web-design` |
| API y contratos cliente-servidor | `vektra-api-contracts`, `vektra-api-security`, `vektra-security-review` |
| Ingesta CSV/Excel/Sheets, fuentes de datos | `vektra-data-ingestion` |
| Semántica de datos / explanations de negocio | `vektra-data-semantics` |
| Alembic y modelos | `vektra-database-migrations` |
| Sandbox y código generado por IA | `vektra-llm-sandbox-hardening` |
| Export PDF / PowerPoint | `vektra-exports-design` |
| Android / Compose | `android-material3-compose`, `android-architecture-mvvm`, `android-mobile-hardening` |
| Verificación antes de cerrar | `vektra-code-verification` |
| Auditoría de planes | `vektra-critical-audit` |
| Modelos de IA, whitelist, deprecaciones, migración | `vektra-gemini-model-lifecycle` |

## Antes de decir "terminado"

```powershell
server\.venv\Scripts\python.exe -m py_compile <archivos modificados>
server\.venv\Scripts\python.exe -m pytest server\tests -q
cd client; npm run lint; npm run build
```

Casos que no pueden fallar: NaN/inf en el motor de análisis, `decrypt_key` roto → **HTTP 400
limpio** (nunca claves corruptas a Gemini/Mistral), y timeout de 10 s en el sandbox.

## Documentación

`docs/PROBLEMAS_CONOCIDOS.md` · `docs/GUIA_AGENTE_REFERENCIA_RAPIDA.md` ·
`docs/MANUAL_PRUEBAS_AJUSTES.md` · `docs/BITACORA_2026-11-07_AUDITORIA_Y_VISION_VEKTRA.md` ·
`PLAN_P11_UPLOAD_SEGURO.md` · `AGENTS.md` (reglas para Codex/Antigravity).
