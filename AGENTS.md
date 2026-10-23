# AGENTS.md

Workspace rules for coding agents and humans. Read this before the first edit.

## What this workspace is

One product: an onboarding assistant for the MAX messenger.

- `apps/api/` — webhook API, scenario engine, retrieval, answer generation, admin API.
- `apps/admin/` — the recruiter cockpit. Not a chatbot; it reads the admin API.
- `knowledge/` — the non-public company corpus that the assistant may answer from. Data, not code.
- `docs/` — the specification of record: architecture, contracts, decisions, runbooks, evals.

The repository is the only source of truth. A fact that lives only in a chat message does not exist.

## Read before editing

| About to touch | Read first |
|---|---|
| anything | this file, `docs/README.md` |
| scenario steps or timers | `docs/product/scenarios.md`, `docs/contracts/scenario.schema.json` |
| retrieval, chunking, citations | `docs/architecture.md`, `docs/decisions/0003-hybrid-retrieval.md` |
| prompts, tone, refusals | `docs/prompts/`, `docs/product/answer-policy.md`, `docs/evals/README.md` |
| webhook, MAX payloads | `docs/contracts/max-api.md`, `docs/decisions/0002-async-webhook.md` |
| admin API or cockpit | `docs/contracts/admin-api.md`, `docs/product/roles.md` |
| the database | `apps/api/onboarding/app/db/`, `docs/runbooks/migrate.md` |
| a deployment | `docs/runbooks/deploy.md` |
| a claim about quality | `docs/evals/README.md`, `docs/measurements/` |

## Hard rules

1. **`core/` has no I/O.** No `httpx`, no SQLAlchemy, no `datetime.now`, no `random`, no logging
   inside `apps/api/onboarding/core/`. Time, network, and storage arrive as arguments or ports.
2. **`knowledge/` is data.** Never edit it in the same commit as code. Every document keeps a
   frontmatter block with `id`, `owner`, `audience`, `valid_from`.
3. **Contracts precede code.** Schemas live in `docs/contracts/`. If the code needs a field the
   schema does not have, change the schema first.
4. **Prompts are versioned files.** No prompt string in Python. A prompt change is a new version
   plus an eval run recorded in `docs/measurements/`.
5. **Never invent a number.** A measurement needs a command, an environment, and a commit.
   `--offline` proves the contract, not the quality.
6. **No secrets in git.** `.env.local`, bot tokens, provider keys, and the webhook secret stay out.
   Error messages must not echo them either.
7. **One repository.** No nested `.git`, no submodules.
8. **Docs are English.** `knowledge/` and user-facing copy are Russian. Raw inputs keep their
   original language. Conversation with the user follows the user.

## Commands

```bash
make install                       # uv sync, creates .venv
make check                         # ruff, mypy, pytest, docs link check
make eval                          # retrieval, generation, escalation on the golden set
make eval-retrieval                # retrieval only, no provider key needed
make run                           # uvicorn on :8000
make up / make down                # docker compose stack
make docs                          # docs index completeness and dead-link check
make eval-sentiment                # PROVIDER=keyword|prompt|jev SPLIT=dev|test REPEAT=n
```

## Network

Every provider call leaves through a SOCKS tunnel; a direct request fails before it reaches the
provider. Export it for anything that calls a model, an embedder, or a reranker:

```bash
export HTTPS_PROXY=socks5h://127.0.0.1:1080
```

`httpx` reads that variable on its own (`socksio` is installed), so application code needs no proxy
setting and no proxy argument. `curl` needs `--proxy socks5h://127.0.0.1:1080`.

Measured on 2026-10-23: without the tunnel, `openrouter.ai` answers `403 Access denied by security
policy` for `/systemone`, `/key`, `/rerank`, and `/chat/completions` alike, and `httpx` raises
`ProxyError 503`. That is this machine's egress, not the provider and not the adapter: the same key
returns `200` through the tunnel. Treat a `403` in a measurement log as a missing tunnel, then look
at the provider.

## Where changes go

| Change | Home |
|---|---|
| behaviour of the bot | `apps/api/onboarding/` |
| a new scenario | `docs/product/scenarios.md` + `apps/api/scenarios/` |
| a new answer rule | `docs/product/answer-policy.md` + a prompt version |
| a decision that reverses an accepted one | a new ADR in `docs/decisions/`, never an edit |
| a new fact about MAX | `docs/contracts/max-api.md` with the source URL |
| a measured result | `docs/measurements/` with command, environment, commit |
| a failure and its fix | `docs/incidents/` with the proof the fix works |

## Definition of done

1. `make check` passes.
2. New behaviour has a test in `apps/api/tests/` or an eval case in `docs/evals/golden.yaml`.
3. The affected doc is updated, and new docs are listed in `docs/README.md`.
4. Accepted ADRs are untouched; supersede them instead.
5. The commit is Conventional Commits, English, header only, ≤72 characters.
