# Architecture

## Context

Newcomers ask questions during their first weeks; recruiters track progress and intervene when
someone stalls. The assistant answers from the company knowledge base in the company tone and
escalates anything it cannot ground. MAX is the only client. The recruiter cabinet is a separate
web app that reads the admin API.

## Building blocks

```
MAX ──webhook──► api ──► Postgres: events + jobs
                              │
                              ▼
                        worker ──► scenario engine ──► outbox ──► MAX API
                              │            │
                              │            └──► retrieval ──► one model call ──► grounding
                              └──► reminder tick ──► jobs (timeout)

recruiter cabinet ──► admin API ──► Postgres: runs, questions, audit
```

Two processes from one image:

| Process | Responsibility |
|---|---|
| `api` | MAX webhook, admin API, health. Never calls the model. |
| `worker` | claim jobs, apply scenario transitions, answer questions, dispatch the outbox, tick due reminders. |

They share code and the database, not memory. The reminder tick runs inside the worker loop every
25 iterations; it is not a third process.

## A message, end to end

1. `api` receives `POST /webhook`, checks `X-Max-Bot-Api-Secret` in constant time, parses the
   update, and inserts an `events` row plus a `jobs` row in one transaction. It answers `200`
   immediately. A duplicate delivery fails the `events` primary key and exits without a job.
2. `worker` claims the job with `FOR UPDATE SKIP LOCKED`, loads the run, and applies the scenario
   transition: a pure function `(scenario, step_state, event) -> transition`.
3. The transition's new state and reminder are stored first. Only then are messages written to the
   `messages` outbox, one transaction per message. A crash between the two repeats a message at
   worst; it never loses a step.
4. For a question, retrieval runs: ACL and validity predicates in SQL, vector and lexical search,
   reciprocal rank fusion, then one model call with a versioned prompt and a JSON answer contract.
5. The answer is validated: every citation in the JSON list and every inline `[doc#N]` token
   must be a chunk that retrieval returned, and confidence must clear `ANSWER_MIN_CONFIDENCE`.
   Otherwise the decision degrades to escalation with the matching copy.
6. A dispatcher sends outbox rows to MAX with per-chat pacing of 2 messages per second and
   exponential retry, up to 5 attempts. Delivery is at-least-once.
7. The answerer writes an audit row: prompt version, retrieved count, citation count, tokens,
   cost, latency. The action executor writes the question row that feeds the cabinet.

## Invariants

1. `api` never calls the model and never waits for MAX delivery.
2. `core/` is pure: no I/O, no clock, no randomness. `tests/test_core_purity.py` enforces it.
3. A live run never changes scenario version; the catalog can hold several versions at once.
4. An answer without a citation from the retrieved set is not sent.
5. State is persisted before the message that announces it.
6. Knowledge documents never leave their audience. ACL and validity are SQL predicates applied
   before ranking, not filters on the result.
7. Secrets live in `SecretStr` and are never written to logs or audit fields.

## Failure modes

| Failure | Behaviour |
|---|---|
| MAX retries a delivery | `events` primary key rejects it; no second job |
| MAX API 5xx or timeout | message row stays pending, retried with backoff, parked after 5 attempts |
| Model provider 5xx, timeout, or open breaker | one retry, then an escalation with `unavailable` copy |
| Model returns ungrounded or malformed JSON | answer rejected, escalation, `answer_rejected` audit row |
| Embedder or database fails during retrieval | escalation with `unavailable` copy |
| Knowledge is stale | `valid_to` excludes the document; the question escalates |
| Worker backlog | jobs wait; the webhook keeps accepting; state is not lost |
| Postgres unavailable | webhook answers 503; MAX retries |
| A scenario file is invalid | the process refuses to start |
| A job payload is invalid | job fails, is retried, then parked with `last_error` |

## Provider compatibility

The gateway speaks the OpenAI chat-completions dialect. GigaChat and OpenAI need only a base URL
and a key. Some OpenAI-compatible gateways also require static routing headers, supplied as a JSON
object in `LLM_EXTRA_HEADERS`; authentication and content headers cannot be overridden there.
A gateway may wrap the completion in `{"success": true, "data": {...}}`; the gateway unwraps it,
rejects `success: false`, and keeps token usage from either level.

## Deliberately absent

No message broker, no separate vector database, no orchestrator, no microservices. One Postgres
holds state, vectors, queue, outbox, questions, and audit; the workload does not justify more. See
[decision 0005](decisions/0005-single-postgres.md).

## Module map

| Path | Responsibility |
|---|---|
| `apps/api/onboarding/core/` | pure domain: models, scenario parser, transitions, chunking, ranking, grounding, prompt rendering, breaker, ACL |
| `apps/api/onboarding/ports.py` | protocols for clock, model, embedder, knowledge, messaging, repositories, audit |
| `apps/api/onboarding/app/max/` | MAX HTTP client, update parsing, keyboards |
| `apps/api/onboarding/api/` | FastAPI app, webhook, admin routes, bearer auth, response schemas |
| `apps/api/onboarding/app/db/` | SQLAlchemy models, repositories, queue, outbox, scheduler, pgvector knowledge base |
| `apps/api/onboarding/app/worker/` | answer pipeline, action executor, run service, job runner, worker loop |
| `apps/api/onboarding/app/llm/` | provider adapters, gateway with retry/breaker/cost, offline extractive provider, embeddings |
| `apps/api/onboarding/app/knowledge/` | corpus loading, chunking pipeline, local in-memory backend |
| `apps/api/onboarding/scenarios/` | versioned scenario YAML |
| `apps/api/onboarding/cli.py` | `ingest`, `seed`, `demo`, `subscribe`, `check` commands |
| `apps/admin/` | recruiter cabinet (React + TypeScript) |
| `knowledge/` | the corpus, one Markdown file per document |

## Performance targets

One question is one retrieval, one model call, one validation, one send. Target p95 end-to-end
delivery is 3 seconds with a warm model. The webhook itself stays under 200 ms: it does two
inserts and returns.
