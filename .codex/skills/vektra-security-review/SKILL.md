---
name: vektra-security-review
description: Review and harden Vektra BI security. Use when changing or reviewing authentication, authorization, endpoint ownership, API keys, secrets, CORS, rate limits, logs, production configuration, destructive endpoints, or any server/client boundary in this FastAPI + Next.js BI application.
---

# Vektra Security Review

Apply this checklist before editing security-sensitive code and again before finishing.

## Project Rules

- Treat the backend token identity as the only source of truth. Do not trust `user_id` sent by the client.
- Require every user-owned DB query to include ownership checks such as `Model.user_id == authenticated_user`.
- Protect destructive/admin endpoints with authentication, authorization, and rate limiting. Remove dev-only endpoints from production paths.
- Never log raw API keys, bearer tokens, connection strings, database URLs, emails in high-volume logs, uploaded data samples, or LLM prompts containing secrets.
- Require `AUTH_SECRET` or `NEXTAUTH_SECRET`, `ENCRYPTION_KEY`, production database config, and explicit allowed origins in production.
- Keep CORS explicit. Do not use wildcard origins with credentials.
- Keep error responses generic in production and detailed only in local development logs after secret filtering.
- Do not add fallback secrets, default admin users, or permissive production bypasses.

## Review Workflow

1. Identify trust boundaries: browser, NextAuth, FastAPI, database, file storage, LLM providers, sandbox worker.
2. Trace identity from `client/src/auth.ts` to FastAPI authorization helpers.
3. Check endpoint inputs and outputs for spoofable identity, secret exposure, unsafe file paths, and mass assignment.
4. Confirm rate limits exist for expensive endpoints, uploads, LLM calls, exports, simulations, and config mutation.
5. Add or update tests for ownership failures, missing token, wrong user token, and destructive endpoint protection.

## Red Flags

- Endpoint accepts `user_id` and uses it directly.
- Query fetches by resource id without `user_id`.
- Endpoint mutates or deletes data without auth.
- Raw `str(e)` is returned to clients in production paths.
- API keys are passed repeatedly from frontend when encrypted backend storage already exists.
- Development bypass depends only on missing environment variables.
