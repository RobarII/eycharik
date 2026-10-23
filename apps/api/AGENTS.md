# apps/api/AGENTS.md

Narrows the root `AGENTS.md`. On a conflict this file wins.

## Boundaries

- `onboarding/core/` — pure. Standard library and sibling `core` imports only.
- `onboarding/ports.py` — protocols only; no implementations, no imports from `app/`.
- `onboarding/app/` — every effect: HTTP, SQL, model calls, clock, logging.
- `onboarding/api/` — FastAPI routers; no business rules beyond request mapping.

## Rules

1. A new effect is a port plus an implementation. Do not import `app/` from `core/`.
2. SQL only in `app/db/`. Repositories accept domain types and return domain types.
3. Every production model call goes through `app/llm/gateway.py`: timeout, one retry, circuit
   breaker, cost. `app/llm/extractive.py` is the offline exception (ADR 0007): it may serve the
   local demo, including the webhook path, but `Settings` refuses to boot with it when
   `ENVIRONMENT=production`.
4. Every outbound MAX message is written to the outbox before it is sent.
5. A prompt is loaded by name and version; a string literal prompt is a review blocker.
6. Tests for `core/` use no fixtures beyond data. Tests with Postgres are `-m integration`.

## Commands

```bash
cd apps/api
uv run pytest -q -m "not integration and not eval"
uv run ruff check .
uv run mypy onboarding/core onboarding/ports.py
```
