# Agent Instructions

This repository contains project-specific agent skills under `.codex/skills`.
Before modifying the project, read and apply the relevant skill files for the task.

## Skill Routing

### Frontend & UI / UX
- Use `.codex/skills/vektra-product-design/SKILL.md` for Vektra-specific frontend UI, styling, dashboards, chat, settings, and component states.
- Use `.codex/skills/universal-premium-web-design/SKILL.md` for general, high-fidelity web UI layouts, typography, CSS glassmorphism, animations, and responsive web elements.
- Use `.codex/skills/android-material3-compose/SKILL.md` for native Android UI layouts, Material Design 3 styling, Compose layouts, state hoisting, and mobile screens.

### Security & Hardening
- Use `.codex/skills/vektra-security-review/SKILL.md` for security, auth, backend database ownership, CORS configs, User-Agents, and mobile SSL pinning.
- Use `.codex/skills/android-mobile-hardening/SKILL.md` for mobile app security, AndroidManifest permissions, local SQLCipher/Room database encryption, and R8/ProGuard obfuscation rules.
- Use `.codex/skills/vektra-llm-sandbox-hardening/SKILL.md` for LLM-generated code execution, subprocess sandboxing, unsafe output handling, and simulations.

### Architecture & Refactoring
- Use `.codex/skills/android-architecture-mvvm/SKILL.md` for mobile app structure, MVVM architecture in Kotlin, Coroutines, StateFlow, and Hilt dependency injection.
- Use `.codex/skills/vektra-architecture-refactor/SKILL.md` for large backend/database refactoring, migrations, models, workers, and module boundaries.
- Use `.codex/skills/multiplatform-monorepo-sync/SKILL.md` for monorepo configuration, OpenAPI client generation for TS/Kotlin, and localization (i18n) sync.

### Data & Connectivity
- Use `.codex/skills/vektra-data-ingestion/SKILL.md` for CSV/Excel uploads, Google Sheets, SQL connections, quotas, and cleanup.
- Use `.codex/skills/vektra-api-contracts/SKILL.md` for frontend/backend TS client bindings, Pydantic schemas, and analysis endpoints.
- Use `.codex/skills/universal-api-mocking-and-testing/SKILL.md` for MSW mocking in web tests and OkHttp Interceptors/MockWebServer in Android tests.
- Use `.codex/skills/deployment-and-ci-cd-pipelines/SKILL.md` for configuring GitHub Actions, Docker containers, and Gradle release signing / Fastlane beta uploads.

### Alignment & Agent Control
- Use `.codex/skills/known-issues-registry/SKILL.md` **FIRST, for every task**: mandatory "known issues first" rule (`docs/PROBLEMAS_CONOCIDOS.md`), no repeated mistakes, close issues only with evidence.
- Use `.codex/skills/agent-stability-and-guidance-control/SKILL.md` for AI agent behavior, preventing scope creep, strictly following instructions, and respecting dependency security rules.
- Use `.codex/skills/user-interaction-protocol/SKILL.md` for standardizing user requests, ensuring quality standards (9-10/10) and executing task flows without regressions.

## General Rules

- **REGLA 0 — Problemas conocidos primero (BLOQUEANTE):** Antes de leer cualquier otra skill, planificar o modificar un archivo, el agente DEBE leer `docs/PROBLEMAS_CONOCIDOS.md` y `.codex/skills/known-issues-registry/SKILL.md`. Debe citar los `P-XX` abiertos que toquen la tarea, no empeorarlos, y registrar cualquier hallazgo nuevo **antes** de corregirlo. Ningún problema se marca `CERRADO` sin evidencia (test o comando reproducible). **Excepción de evolución:** si el ajuste nuevo justificado choca con un comportamiento o test viejo, manda el ajuste nuevo y el viejo se actualiza en el mismo cambio (documentado en el registro); nunca se revierte un arreglo de seguridad ni se debilita un test de regresión.
- **Lectura Inicial Obligatoria:** Al iniciar cualquier interacción o tarea en el proyecto, el agente DEBE leer en primer lugar la skill del protocolo de interacción `.codex/skills/user-interaction-protocol/SKILL.md` para coordinar el trabajo de forma óptima.
- **Lectura de Skills Relacionadas:** Todos los prompts o tareas complejas deben iniciarse leyendo las skills relacionadas bajo `.codex/skills/` para evitar alucinaciones y asegurar consistencia con el diseño del proyecto.
- **Creación de Skills Proactiva:** Si detectas que se están realizando tareas manuales o lógicas repetitivas, debes proponer y preguntar explícitamente al usuario si se puede consolidar un nuevo archivo de skill en `.codex/skills/` para automatizarlo.
- Prefer small, safe, incremental changes over rewrites.
- Preserve current behavior unless the task explicitly changes it.
- Do not trust client-supplied `user_id`; backend identity must come from the authenticated token.
- Do not expose or log secrets.
- Do not introduce production bypasses, fallback secrets, or unauthenticated destructive endpoints.
- Keep generated files, virtual environments, logs, caches, and scratch artifacts out of source control.
- Add or update focused tests when changing security, data ingestion, API contracts, sandbox behavior, or shared architecture.

## How To Use From Other Agents

If your tool does not automatically understand Codex skills, explicitly read the relevant `SKILL.md` files listed above and treat them as mandatory project instructions for the current task.



