# Architecture

## Context

Newcomers ask questions during their first weeks; recruiters track progress and intervene when
someone stalls. The assistant answers from the company knowledge base, in the company tone, and
escalates anything it cannot ground. MAX is the only client; there is no mobile app to build.

## Building blocks

```
MAX ──webhook──► gateway ──► queue (Postgres) ──► worker ──► MAX API
                    │                              │
                    │                              ├─ scenario engine
                    │                              ├─ retrieval + answer
                    │                              └─ escalation
                    └─ processed_events            │
                                                   ▼
                                   Postgres: runs, events, outbox,
                                             knowledge, chunks, audit
scheduler ──► outbox (due reminders) ──► queue
admin UI ──► admin API ──► Postgres
```

One deployable image runs three processes: `gateway` (HTTP, fast), `worker` (slow work), and
`scheduler` (timers). They share code and the database, not memory.

## A message, end to end

1. `gateway` receives `POST /webhook/max`, checks `X-Max-Bot-Api-Secret`, parses the update into a
   typed event, inserts a `processed_events` row and a `jobs` row in one transaction, returns
   `200` in the same millisecond. A duplicate delivery hits the unique index and exits early.
2. `worker` claims the job with `FOR UPDATE SKIP LOCKED`, loads the run, and applies the scenario
   transition in memory: a pure function `(step_state, event) -> decision`.
3. A `decision` is one of: `send`, `wait`, `escalate`, `complete`. The worker persists the new
   state and the outbox rows (messages, timers) in one transaction.
4. When the decision is an answer, retrieval runs: ACL filter, hybrid search, rerank, then one
   model call with a versioned prompt and a JSON answer contract.
5. The answer is validated: citations must be a subset of the retrieved chunk ids; otherwise the
   decision degrades to escalation. The validated answer is sent to MAX.
6. Every step writes an audit row: trace id, run id, prompt version, retrieved chunks with scores,
   token counts, cost, latency.

## Invariants

1. The gateway never calls the model and never blocks on the network beyond MAX delivery.
2. `core/` is pure: no I/O, no clock, no randomness. All of it is testable without a database.
3. A live run never changes scenario version.
4. An answer without a citation from the retrieved set is not sent.
5. An outbound message is written to the outbox before it is sent; sending is at-least-once and
   message ids are deduplicated by `(run_id, step_id, attempt)`.
6. Knowledge documents never leave their audience. The ACL filter is applied in SQL before ranking.
7. Secrets never reach logs, traces, or error payloads.

## Failure modes

| Failure | Behaviour | Detection |
|---|---|---|
| MAX webhook retries a delivery | duplicate ignored by `processed_events` | `gateway_duplicates_total` |
| MAX API 5xx or timeout | outbox row stays pending, exponential retry, max 5 attempts | `outbox_pending_age_seconds` |
| Model provider 5xx / timeout | one retry, then cached answer, then escalation with a human handoff | `llm_failures_total`, `escalations_total` |
| Model returns ungrounded JSON | answer rejected, escalation | `answer_rejected_total` |
| Knowledge is stale | document is excluded by `valid_to`; question escalates | `kb_documents_expired` |
| Worker backlog | admins see rising queue age; gateway keeps accepting | `jobs_pending_age_seconds` |
| Postgres unavailable | gateway returns 503, MAX retries; no data loss | `db_errors_total` |

## Deliberately absent

No message broker, no vector database, no orchestrator, no microservices. One Postgres holds
state, vectors, queue, and outbox; the scale of an onboarding bot does not justify more. See
[decision 0005](decisions/0005-single-postgres.md).

## Module map

| Path | Responsibility |
|---|---|
| `apps/api/onboarding/core/` | pure domain: scenario transitions, chunking, ranking fusion, grounding, prompt rendering |
| `apps/api/onboarding/ports.py` | protocols for clock, model, embedder, knowledge, messaging, repositories |
| `apps/api/onboarding/app/max/` | MAX HTTP client and payload mapping |
| `apps/api/onboarding/app/gateway/` | webhook validation, idempotency, enqueue |
| `apps/api/onboarding/app/worker/` | job handling, scenario execution, answer pipeline |
| `apps/api/onboarding/app/scheduler/` | due-reminder loop |
| `apps/api/onboarding/app/db/` | SQLAlchemy models, repositories, migrations |
| `apps/api/onboarding/app/llm/` | provider adapters behind one interface |
| `apps/api/onboarding/app/admin/` | admin API and RBAC |
| `apps/admin/` | recruiter cockpit |
