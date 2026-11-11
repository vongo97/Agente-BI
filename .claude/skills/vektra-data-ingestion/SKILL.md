---
name: vektra-data-ingestion
description: Secure and maintain Vektra BI data ingestion. Use when changing CSV/Excel uploads, Google Sheets, SQL connections, data source storage, file parsing, quotas, sessions_cache, data_sources, dataframe persistence, cleanup, or import/export flows.
---

# Vektra Data Ingestion

Data ingestion is a security boundary. Uploaded files, sheet URLs, SQL URLs, and parsed datasets are untrusted.

## Upload Rules

- Require authentication before upload or data-source mutation.
- Allow only business-required extensions: CSV and Excel unless a new type is explicitly justified.
- Do not trust `Content-Type`; validate extension plus parser behavior.
- Generate backend filenames. Do not preserve user filenames as storage paths.
- Restrict filename length and characters.
- Enforce per-file, per-user total storage, table count, row count, column count, and cell count limits.
- Store files outside the webroot and access them through DB ids, not raw paths.
- Clean up physical files when deleting data sources.

## Connector Rules

- For SQL, sanitize connection error messages and never log credentials.
- Validate and constrain SQL connection URLs before storing them.
- For Google Sheets, require public/read-only input and enforce max cells before analysis.
- Keep source ownership checks on every operation.

## Persistence Rules

- Do not persist long-lived sessions as `pickle`.
- Prefer metadata in SQL tables and dataframe payloads in Parquet/Arrow/object storage.
- Keep in-memory caches as optional acceleration only; the app must recover from process restart.

## Tests To Add

- Reject wrong extension, oversize files, spoofed MIME, too many sources, and quota overflow.
- Verify user A cannot list/delete/load user B sources.
- Verify parser failure returns a safe message.
- Verify deleting a source removes metadata and safe physical files only.
