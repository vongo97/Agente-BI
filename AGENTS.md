# Agent Instructions

This repository contains project-specific agent skills under `.codex/skills`.
Before modifying the project, read and apply the relevant skill files for the task.

## Skill Routing

- Use `.codex/skills/vektra-product-design/SKILL.md` for frontend UI, styling, dashboards, chat, settings, reports, simulation screens, visual summaries, spacing, colors, and component states.
- Use `.codex/skills/vektra-security-review/SKILL.md` for authentication, authorization, user ownership, secrets, API keys, CORS, rate limits, logs, production configuration, and destructive endpoints.
- Use `.codex/skills/vektra-llm-sandbox-hardening/SKILL.md` for LLM-generated code execution, prompts, subprocess sandboxing, unsafe output handling, pickle/session serialization, visual summaries, and simulations.
- Use `.codex/skills/vektra-data-ingestion/SKILL.md` for CSV/Excel uploads, Google Sheets, SQL connections, data-source storage, parsing, quotas, sessions, cleanup, imports, and exports.
- Use `.codex/skills/vektra-api-contracts/SKILL.md` for frontend/backend contracts, `client/src/lib/api.ts`, FastAPI routers, Pydantic schemas, token handling, user config, dashboard APIs, analysis APIs, and simulation APIs.
- Use `.codex/skills/vektra-architecture-refactor/SKILL.md` for large refactors, services, repositories, database models, Alembic migrations, workers, tests, and module boundaries.

## General Rules

- Prefer small, safe, incremental changes over rewrites.
- Preserve current behavior unless the task explicitly changes it.
- Do not trust client-supplied `user_id`; backend identity must come from the authenticated token.
- Do not expose or log secrets.
- Do not introduce production bypasses, fallback secrets, or unauthenticated destructive endpoints.
- Keep generated files, virtual environments, logs, caches, and scratch artifacts out of source control.
- Add or update focused tests when changing security, data ingestion, API contracts, sandbox behavior, or shared architecture.

## How To Use From Other Agents

If your tool does not automatically understand Codex skills, explicitly read the relevant `SKILL.md` files listed above and treat them as mandatory project instructions for the current task.
