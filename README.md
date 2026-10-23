# MAX onboarding assistant

AI assistant for employee onboarding in the MAX messenger: onboarding scenarios for newcomers,
a recruiter cockpit, and a retrieval-grounded assistant over the company knowledge base.

Built for the "AI assistant in MAX" case (ООО «Группа ПОЛИПЛАСТИК»).

## Map

| Path | What | Mutable |
|---|---|---|
| `docs/` | architecture, contracts, decisions, runbooks, evals | yes |
| `knowledge/` | non-public company corpus served to the assistant | yes, with owner review |
| `apps/api/` | the service: webhook API, scenario engine, RAG, admin API | yes |
| `apps/admin/` | recruiter cockpit | yes |
| `docs/evals/` | golden set and its runner contract | yes |
| `infra/demo/` | demo employees for `make seed` | yes |

## Start here

| Question | File |
|---|---|
| What are we building and why? | `docs/architecture.md` |
| How do I work in this repository? | `AGENTS.md` |
| Where does a fact live? | `docs/README.md` |
| What is the bot allowed to answer? | `docs/product/answer-policy.md` |

## Quick commands

```bash
make install      # create the virtual environment
make check        # ruff, mypy, unit tests, docs links
make eval         # golden-set retrieval, generation, escalation
make ingest       # index knowledge/ into pgvector
make demo         # three employees, one completed run, a question queue
make run          # api with reload on :8000
make worker       # job loop, outbox dispatcher, reminder tick
make admin-install # cabinet dependencies
make admin-dev    # recruiter cabinet on :5173
make up           # postgres + migrate + api + worker + cabinet in docker
```

Offline demo in five minutes: [docs/product/demo-script.md](docs/product/demo-script.md).

## Status

Working end to end against a local Postgres with pgvector:

- MAX webhook: secret check, `events` dedupe, durable job enqueue, `200` in milliseconds.
- Scenario engine: versioned YAML, pinned per run, buttons, files, reminders, escalation on timeout.
- Retrieval: frontmatter/JSON Schema corpus, deterministic chunking, pgvector HNSW + Russian
  `tsvector`, RRF, audience and validity as SQL predicates.
- Answering: one model call, JSON contract, citation must come from the retrieved set, escalation
  reasons in product copy, audit row per attempt.
- Recruiter cabinet: runs, per-employee detail, question queue scoped by recruiter or HR.
- Golden set: 11 cases, retrieval recall@5 = 1.00, escalation correctness = 1.00 on the offline
  provider; see `docs/measurements/`.
- Tests: 150+ unit and integration tests; `core/` purity enforced by a test.

Known gaps, stated so nobody assumes otherwise:

- A real MAX bot token and the "MAX для бизнеса" verification are external dependencies. The
  adapter and the webhook are tested against the documented payloads and a local sender.
- GigaChat credentials are not in the repository. `LLM_PROVIDER=extractive` proves the pipeline,
  not the model's answer quality; the online path is one configuration change.
- One worker replica: the MAX pacing state is in-process. More replicas need a shared limiter.
- File upload is described by the scenario, not implemented against MAX.
- No production deployment has happened. Nothing here claims one.
