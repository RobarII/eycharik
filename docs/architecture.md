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
                            │
                            └──► Postgres: kb_files + extract_document job
                                       │
                                       ▼
                              worker: read ──► decide ──► index ──► kb_extractions
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
   reciprocal rank fusion, an optional hosted rerank (ADR 0008), then one model call with a
   versioned prompt and a JSON answer contract.
5. The answer is validated: every citation in the JSON list and every inline `[doc#N]` token
   must be a chunk that retrieval returned, and confidence must clear `ANSWER_MIN_CONFIDENCE`.
   Otherwise the decision degrades to escalation with the matching copy.
6. A dispatcher sends outbox rows to MAX with per-chat pacing of 2 messages per second and
   exponential retry, up to 5 attempts. Delivery is at-least-once.
7. The answerer writes an audit row: prompt version, retrieved count, citation count, tokens,
   cost, latency. The action executor writes the question row that feeds the cabinet.
8. The cabinet closes a question: `resolved_at`, `resolved_by`, `resolution`, the reply as a
   `messages` row, and `question_resolved` in one transaction. The dispatcher delivers the reply
   with the same pacing and retries as any scenario message.

## An uploaded file, end to end

The corpus is markdown, but recruiters bring PDFs and scans. Extraction is the bridge, and it is an
adapter, not a step in a request (ADR 0015).

1. `POST /admin/api/knowledge/files` (HR only) reads the file and the frontmatter as `multipart`.
   Metadata is validated against `doc.schema.json` — the same contract a committed document obeys —
   before anything is stored. A wrong format answers `415`, an oversized file `413`.
2. The bytes go to `kb_files`, keyed by their SHA-256. Re-uploading the same bytes returns the same
   id and queues no second job.
3. The endpoint enqueues `extract_document` and answers `202`. It never waits for recognition.
4. The worker reads the blob and looks up `kb_extractions` by `(content_hash, profile_hash)`. A hit
   finishes the job without touching the file.
5. `RoutingExtraction` reads the file with the cheapest reader that owns the format: pdfium text
   layer, or `python-pptx` shapes. Pure code decides the route: enough text means no recognition.
   Otherwise the pages are rasterized, gated on the pre-recognition checks the profile enables, and
   recognized. There is no glare score: white paper would read as "100% glare". Overexposure is
   caught after recognition, by the engine's own per-line confidence.
6. `accept` decides: one page under the confidence floor, or coverage under the policy, refuses the
   whole document. A refusal is a value with a reason, recorded and shown in the cabinet.
7. Only an accepted document is rendered to markdown (`compose.render_document`) and indexed through
   the same `ingest_document` choke point the corpus directory uses. `knowledge/` is never written.
8. The outcome — `indexed` or `rejected`, with engine, route, pages, and confidence — is cached and
   audited (`document_extracted`, `document_rejected`, `document_extraction_cached`).

Small fixtures beside the tests (`apps/api/tests/files.py`) generate the PDFs and decks, so a test
that reads a document says how that document was made.

## Invariants

1. `api` never calls the model and never waits for MAX delivery.
2. `core/` is pure: no I/O, no clock, no randomness. `tests/test_core_purity.py` enforces it.
3. A live run never changes scenario version; the catalog can hold several versions at once.
4. An answer without a citation from the retrieved set is not sent.
5. State is persisted before the message that announces it.
6. Knowledge documents never leave their audience. ACL and validity are SQL predicates applied
   before ranking, not filters on the result.
7. Secrets live in `SecretStr` and are never written to logs or audit fields.
8. A model's behaviour lives in a profile file, not in a Python branch: no model name in `app/`.
9. The cabinet never calls MAX. Every outbound message, including a recruiter's reply, is an
   outbox row written in the transaction that records the intent.

## Failure modes

| Failure | Behaviour |
|---|---|
| MAX retries a delivery | `events` primary key rejects it; no second job |
| MAX API 5xx or timeout | message row stays pending, retried with backoff, parked after 5 attempts |
| Model provider 5xx, timeout, or open breaker | one retry, then an escalation with `unavailable` copy |
| Model returns ungrounded or malformed JSON | answer rejected, escalation, `answer_rejected` audit row |
| Embedder or database fails during retrieval | escalation with `unavailable` copy |
| Reranker fails or answers nonsense | hybrid order stands, `rerank_failed` in the audit |
| Knowledge is stale | `valid_to` excludes the document; the question escalates |
| Worker backlog | jobs wait; the webhook keeps accepting; state is not lost |
| Postgres unavailable | webhook answers 503; MAX retries |
| A scenario file is invalid | the process refuses to start |
| A job payload is invalid | job fails, is retried, then parked with `last_error` |
| A recruiter resolves a question twice | first commits the reply; second gets `409`, no duplicate |
| An employee leaves mid-run | soft delete closes the run and purges questions; later inbound events are ignored |
| The retention pass fails | logged, retried next tick; committed batches stay committed |

## Model profiles

A model is data, not a code path (ADR 0013). Each model is a YAML file under
`apps/api/model-profiles/<role>/`, validated against
[`contracts/model-profile.schema.json`](contracts/model-profile.schema.json) before use. The file
states the wire dialect, the capabilities the model actually has, the generation envelope, and the
prices. `LLM_PROFILE`, `EMBED_PROFILE`, and `RERANK_PROFILE` choose one; the gateway, the embedder,
and the reranker read it and never branch on a model name.

| Role | What the profile decides | What the environment keeps |
|---|---|---|
| `answer` | dialect, json mode, token field, reasoning effort, temperature, token cap, timeout, retries, prices | base URL, key, breaker, static headers |
| `embed` | dialect, model id, vector width, timeout | base URL, key |
| `rerank` | model id, timeout | base URL, key, whether the stage runs at all |

Resolution order for every value: an explicit environment value, then the profile, then the
default. An invalid or missing profile stops the process at startup, like an invalid scenario.
`EMBED_DIM` and the profile's `dim` must agree; a different width is a migration, not a setting.

## Provider compatibility

The gateway speaks the OpenAI chat-completions dialect; `family` in the profile selects the
adapter. GigaChat and OpenAI need only a base URL and a key. Some OpenAI-compatible gateways also
require static routing headers, supplied as a JSON object in `LLM_EXTRA_HEADERS`; authentication
and content headers cannot be overridden there. A gateway may wrap the completion in
`{"success": true, "data": {...}}`; the gateway unwraps it, rejects `success: false`, and keeps
token usage from either level. A model that rejects `response_format` or wants
`max_completion_tokens` is a capability flag in its profile, not a branch in the gateway.

## Deliberately absent

No message broker, no separate vector database, no orchestrator, no microservices. One Postgres
holds state, vectors, queue, outbox, questions, and audit; the workload does not justify more. See
[decision 0005](decisions/0005-single-postgres.md).

## Module map

| Path | Responsibility |
|---|---|
| `apps/api/onboarding/core/` | pure domain: models, scenario parser, transitions, chunking, ranking, grounding, prompt rendering, breaker, ACL |
| `apps/api/onboarding/ports.py` | protocols for clock, model, embedder, knowledge, messaging, repositories, audit; model profile values |
| `apps/api/onboarding/app/max/` | MAX HTTP client, update parsing, keyboards |
| `apps/api/onboarding/api/` | FastAPI app, webhook, admin routes, bearer auth, response schemas |
| `apps/api/onboarding/app/db/` | SQLAlchemy models, repositories, queue, outbox, scheduler, pgvector knowledge base |
| `apps/api/onboarding/app/worker/` | answer pipeline, action executor, run service, job runner, worker loop |
| `apps/api/onboarding/app/llm/` | provider adapters, model profile loader, gateway with retry/breaker/cost, offline extractive provider, embeddings |
| `apps/api/model-profiles/` | one YAML file per model (`answer/`, `embed/`, `rerank/`) and per reader configuration (`extract/`), validated at startup |
| `apps/api/onboarding/app/knowledge/` | corpus loading, chunking pipeline, local in-memory backend |
| `apps/api/onboarding/app/knowledge/extract/` | readers (pdfium, python-pptx), quality gate, recognizer, routing composite, profile loader, markdown assembly |
| `apps/api/onboarding/scenarios/` | versioned scenario YAML |
| `apps/api/onboarding/cli.py` | `ingest`, `extract`, `seed`, `demo`, `subscribe`, `check` commands |
| `apps/admin/` | recruiter cabinet (React + TypeScript) |
| `knowledge/` | the corpus, one Markdown file per document |

## Performance targets

One question is one retrieval, one optional rerank, one model call, one validation, one send.
Target p95 end-to-end delivery is 8 seconds with a hosted model (ADR 0009); the offline extractive
provider reports zero latency by construction. The webhook itself stays under 200 ms: it does two
inserts and returns.
