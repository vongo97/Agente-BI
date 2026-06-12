---
name: vektra-llm-sandbox-hardening
description: Harden Vektra BI LLM-generated code execution and AI output handling. Use when editing server/src/engine/executor.py, prompts, generated Python analysis code, subprocess isolation, pickle/session serialization, LLM tool use, visual summaries, simulations, or any feature that executes, renders, stores, or trusts model output.
---

# Vektra LLM Sandbox Hardening

Treat LLM output as untrusted user input. The model is not a security boundary.

## Required Controls

- Do not execute model output in the web process.
- Prefer an isolated worker with no production secrets, minimal environment, temporary filesystem, fixed timeout, memory limit, CPU limit, and no network unless explicitly needed.
- Validate code with AST allowlists, but do not rely on AST validation alone.
- Block filesystem writes except to a per-run temp directory.
- Block imports by default and allow only approved data/plotting packages.
- Strip sensitive environment variables before subprocess execution.
- Never pass raw credentials, DB URLs, service-role keys, or auth secrets into the execution environment.
- Persist generated figures/results through structured outputs, not arbitrary files.
- Keep concurrency limits for expensive execution.

## Serialization Rules

- Avoid `pickle` for persisted user/session data.
- Prefer Parquet/Arrow for dataframes and JSON for metadata.
- If temporary pickle remains unavoidable inside one isolated execution run, keep it private to that run, size-limited, and never load pickle from user-controlled or cloud-synced paths.

## Prompt And Output Rules

- Prompts must instruct the model to produce bounded, deterministic Python using provided data variables only.
- Validate generated chart JSON before returning it to the client.
- Never render model HTML directly. For Mermaid/SVG, sanitize or use a constrained renderer path.
- Separate narrative from code; do not let narrative influence execution.

## Tests To Add

- Code attempts `import os`, `open`, `eval`, `exec`, `subprocess`, dunder traversal, infinite loops, large allocations, and network imports.
- Generated output tries to leak environment variables.
- Timeout and memory limit failures return safe user-facing messages.
- Pickle/session loading cannot read attacker-controlled paths.
