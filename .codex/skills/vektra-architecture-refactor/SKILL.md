---
name: vektra-architecture-refactor
description: Refactor Vektra BI architecture for maintainability and scale. Use when reorganizing FastAPI routers, services, repositories, database models, Alembic migrations, workers, shared utilities, tests, or when a change touches multiple backend/frontend modules and needs a conservative migration plan.
---

# Vektra Architecture Refactor

Refactor gradually. Preserve working behavior while making boundaries clearer.

## Target Shape

- Routers: HTTP concerns only, dependencies, request parsing, response mapping.
- Services: business workflows such as analysis, dashboard generation, simulation, ingestion.
- Repositories: SQLAlchemy queries and persistence.
- Schemas: Pydantic request and response models.
- Workers: expensive LLM, sandbox, export, and simulation jobs.
- Utilities: small stateless helpers only.

## Backend Rules

- Avoid global mutable state for critical user data. Treat memory caches as disposable.
- Prefer Alembic migrations for schema changes; avoid relying on `Base.metadata.create_all` as migration strategy.
- Keep storage paths, quotas, provider config, and security requirements in typed settings.
- Avoid broad `except Exception` unless the error is logged safely and mapped to a clear domain failure.
- Keep generated artifacts, scratch files, virtualenvs, logs, and caches out of source control.

## Frontend Rules

- Keep API calls in `client/src/lib/api.ts` or a small typed API layer.
- Keep feature state near feature modules unless it is truly global.
- Prefer reusable product components over one-off visual patterns.

## Refactor Workflow

1. Characterize current behavior with focused tests.
2. Extract one boundary at a time.
3. Keep public route behavior stable unless intentionally changing the contract.
4. Run tests and type/lint checks relevant to touched areas.
5. Document removed legacy paths in the final summary.
