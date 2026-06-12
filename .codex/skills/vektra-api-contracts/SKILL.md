---
name: vektra-api-contracts
description: Design and refactor Vektra BI frontend/backend API contracts. Use when editing client/src/lib/api.ts, FastAPI routers, Pydantic request/response schemas, auth token handling, user config, analysis calls, dashboard endpoints, simulation endpoints, or removing client-supplied user_id/API-key flows.
---

# Vektra API Contracts

Make the API boring, explicit, and hard to misuse.

## Contract Rules

- The frontend must not provide identity as authority. Remove `user_id` from new contracts; derive user from the bearer token.
- Prefer JSON request bodies with Pydantic models for structured operations.
- Use multipart/form-data only for actual file uploads or provider APIs that require it.
- Do not require API keys in every analysis request if keys are already stored encrypted in `UserConfig`.
- Return stable response shapes with typed fields. Avoid leaking SQLAlchemy models directly when response shape matters.
- Use consistent error vocabulary: validation error, unauthorized, forbidden, not found, quota exceeded, processing failed.
- Keep route names resource-oriented and versioned under `/api/v1`.

## Refactor Workflow

1. Add new backend schema and route behavior while keeping old callers if needed.
2. Update `client/src/lib/api.ts` as the single frontend API gateway.
3. Update UI callers to stop passing spoofable identity and repeated secrets.
4. Add compatibility tests or endpoint tests.
5. Remove deprecated parameters after callers are migrated.

## Ownership Pattern

- Start endpoint by resolving `authenticated_user = get_authenticated_user()`.
- Call authorization once through a shared dependency/helper.
- Query user-owned resources with both id and `authenticated_user`.
- Return 404 for missing/not-owned resources unless product needs explicit 403.
