# Admin API contract

The recruiter cabinet reads this API. The bot never calls it.

## Authentication

`Authorization: Bearer <token>`. Tokens are configured in `ADMIN_TOKENS` as
`token:role:subject[:YYYY-MM-DD]` entries:

```
ADMIN_TOKENS=dev-recruiter-token:recruiter:rec-1,dev-manager-token:manager:ИТ,dev-hr-token:hr_admin:hr-1:2030-12-31
```

The optional fourth field is the last valid day; the token expires at `00:00` UTC of the next day.
Omitting it is allowed for a local demo, not for a deployment. A token entry with a duplicate token
or a malformed date refuses to start the process.

| Role | Scope |
|---|---|
| `recruiter` | employees whose `recruiter_id` equals the token's subject |
| `manager` | employees of one department: the token's subject is the department name |
| `hr_admin` | every employee and every question |

A token is compared in constant time. An unknown, missing or expired token answers `401`; ten
failed attempts from one peer within a minute answer `429` for the next minute. A run outside the
caller's scope answers `404`, so the existence of another recruiter's employee is not disclosed.

### Session cookie

The cabinet never stores the token in script-reachable storage. It trades it once:

```http
POST /admin/api/session
Content-Type: application/json

{"token": "dev-recruiter-token"}
```

`204` with `Set-Cookie: onboarding_session=<token>; HttpOnly; SameSite=Strict; Path=/admin/api;
Max-Age=43200`, plus `Secure` outside `local`. Every later request may authenticate with that cookie
alone. `DELETE /admin/api/session` clears it and needs no valid token. The `Authorization` header
stays accepted and wins over the cookie when both are present; `docs/decisions/0018` records why the
cookie exists at all.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/admin/api/me` | the caller's role, scope, capabilities and token expiry |
| `POST` | `/admin/api/session` | trade a bearer token for an HttpOnly session cookie |
| `DELETE` | `/admin/api/session` | clear the session cookie |
| `GET` | `/admin/api/runs?limit=50&cursor=&status=all&q=` | runs, newest activity first, paged; `status` is `active`, `completed` or `all`, `q` searches name, role, department and employee id |
| `GET` | `/admin/api/runs/{run_id}` | one run: step, step text, audit events, recent questions |
| `GET` | `/admin/api/questions?status=unanswered&limit=50&cursor=&assignee=any` | questions by status: `unanswered`, `answered`, `all`, paged; `assignee` is `any`, `me` or `unassigned` |
| `PATCH` | `/admin/api/questions/{question_id}/assignee` | claim an open question, hand it to another admin, or clear the owner |
| `POST` | `/admin/api/questions/{question_id}/resolve` | answer an escalated question in MAX and close it |
| `DELETE` | `/admin/api/employees/{employee_id}` | HR offboards an employee: stops the run, deletes the transcript and the queued messages |
| `GET` | `/admin/api/analytics/overview` | seven-day counts: runs, risk levels, unanswered questions, top risk tags |
| `GET` | `/admin/api/digest/weekly?days=7` | signals that deserve a human, one row per employee and step |
| `GET` | `/admin/api/knowledge?limit=100` | active knowledge documents, newest first; `hr_only` is hidden from every non-HR role |
| `POST` | `/admin/api/knowledge` | HR uploads one markdown document with frontmatter; indexed in the request |
| `POST` | `/admin/api/knowledge/files` | HR uploads a PDF or a deck; stored by content hash and queued for extraction |
| `GET` | `/admin/api/knowledge/files/{content_hash}` | what extraction decided about that file, refusals included |
| `GET` | `/healthz`, `/readyz` | liveness and readiness, no auth |

## Paging

`limit` is bounded to `1..200`. `GET /runs` and `GET /questions` are keyset-paged:

```json
{
  "items": [ /* … */ ],
  "next_cursor": "eyJhdCI6IjIwMjYtMTAtMjNUMDk6MDA6MDArMDA6MDAiLCJydW5faWQiOiIwZjBhIn0",
  "total": 128
}
```

- `next_cursor` is `null` on the last page. Pass it back as `cursor=` to get the next one.
- The cursor is opaque: base64url of the last row's sort key. A client must not build or parse one,
  and the server is free to change the key. A malformed cursor answers `400`, never a partial page.
- `total` counts the whole caller scope, not the page: it is what the cabinet prints in a header.
- Paging is keyset, not offset. A run that moves while a recruiter reads page one cannot shift a row
  from page two into a hole, and cannot duplicate one either.
- Runs are ordered by `updated_at` descending, then id: newest activity first. Questions are ordered
  unanswered first, then `asked_at` descending, then id.

Without a cursor the server answers the newest `limit` rows, so a client that ignores paging still
gets a valid page.

`status` and `q` narrow the same statement the cursor pages through, and `total` counts the filtered
scope. A client must not filter a fetched page instead: that silently hides every match after the
first `limit` rows. `q` is a case-insensitive substring match; `%` and `_` are literal.

## Identity and capabilities

`GET /admin/api/me` answers the same principal the token maps to:

```json
{
  "role": "recruiter",
  "subject": "rec-1",
  "scope": { "recruiter_id": "rec-1", "department": null },
  "capabilities": [
    "runs.read",
    "questions.read",
    "questions.resolve",
    "knowledge.read",
    "analytics.read"
  ],
  "expires_at": "2030-12-31T00:00:00Z"
}
```

The cabinet renders actions from `capabilities`, not from a guess about the token. A capability the
server does not grant must never become a button that fails with `403`.

| Capability | `recruiter` | `manager` | `hr_admin` |
|---|---|---|---|
| `runs.read` | yes | yes | yes |
| `questions.read` | yes | yes | yes |
| `questions.resolve` | yes | yes | yes |
| `questions.assign` | yes | yes | yes |
| `knowledge.read` | yes | yes | yes |
| `analytics.read` | yes | yes | yes |
| `knowledge.write` | no | no | yes |
| `employees.offboard` | no | no | yes |

A capability is a rendering hint, never an authorisation. Every endpoint re-checks its own rule, so
a forged capability changes the buttons and nothing else. `expires_at` is `null` only when the token
entry omits the date field, which is allowed for a local demo and not for a deployment.

## Shapes

`RunSummary`:

```json
{
  "run_id": "0f0a6f4e-1b1c-4a58-9d1e-7d6f2a1f9b3c",
  "employee_id": "1001",
  "name": "Анна Смирнова",
  "role": "Инженер-технолог",
  "department": "Производство",
  "step_id": "documents",
  "step_title": "Документы",
  "step_number": 4,
  "steps_total": 6,
  "entered_at": "2026-10-20T09:00:00Z",
  "updated_at": "2026-10-23T08:40:00Z",
  "status": "active"
}
```

`entered_at` is the first day of the run; `updated_at` is the last activity and the field the list is
sorted by. A card that says "N days in the scenario" reads `entered_at`; a card that says "last seen"
reads `updated_at`.

`step_title` is `null` when the pinned scenario version cannot be loaded or the step id is not in
it; the cabinet falls back to `step_id`. `step_number` is 1-based and `0` when the step is unknown.

`RunDetail` extends `RunSummary` with `scenario`, `scenario_version`, `tone`, `step_message`,
`events`, and `questions`. `tone` is `formal` or `informal` and comes from the welcome choice,
pinned on the run like the scenario version. Its questions are only that employee's, limited to the
newest 20.

`Question`:

```json
{
  "id": 42,
  "employee_id": "1001",
  "employee_name": "Анна Смирнова",
  "text": "Сколько дней отпуска?",
  "answered": false,
  "reason": "no_sources",
  "citations": [],
  "asked_at": "2026-10-23T07:12:00Z",
  "resolved_at": null,
  "resolved_by": null,
  "assignee": null
}
```

`assignee` is the admin subject that picked the question up, or `null` when nobody has. It is a
claim, not an authorisation: the resolver still checks the scope, and a claim never prevents a
colleague from answering.

`PATCH /admin/api/questions/{question_id}/assignee` takes `{"assignee": "rec-1"}` or
`{"assignee": null}` and answers `200` with the new owner:

```json
{ "id": 42, "employee_id": "1001", "assignee": "rec-1" }
```

The name must be the subject of a configured admin token; anything else answers `422`
`"assignee is not an admin"`, so a typo cannot invent a queue nobody can filter. The question must
be open and inside the caller's scope: `404` when it is not visible, `409` when it is already
resolved. Both the claim and the release write an audit event (`question_assigned` or
`question_unassigned`) with the question id, the employee id, the new owner and the actor.
`assignee=me` resolves to the caller's own subject on the server; the cabinet never substitutes a
name client-side.

`POST /admin/api/questions/{question_id}/resolve` takes `{"text": "до 2000 символов"}` and answers
`200` with the closed question:

```json
{
  "id": 42,
  "employee_id": "1001",
  "answered": true,
  "resolved_at": "2026-10-23T09:30:00Z",
  "resolved_by": "rec-1"
}
```

The reply is written to the outbox in the same transaction that closes the question, so MAX
delivery keeps its pacing and at-least-once retries. The audit log gets `question_resolved` with
the question id, the employee id, the actor, and the reply length — never the reply text. A
question outside the caller's scope answers `404`; resolving an already closed question answers
`409`. `text` is stripped; an empty reply answers `422`.

`AnalyticsOverview`:

```json
{
  "active_runs": 12,
  "completed_runs": 4,
  "high_risk": 2,
  "medium_risk": 5,
  "unanswered_questions": 3,
  "resolved_questions": 5,
  "top_tags": [{"tag": "access", "count": 4}, {"tag": "manager", "count": 2}],
  "since": "2026-10-16T09:00:00Z"
}
```

The counts cover the window that starts at `since` and come from the audit log, not from a
materialised table. `unanswered_questions` is a live queue size; `resolved_questions` counts replies
a recruiter sent inside the window. A wrong number must be traceable to events.

`DELETE /admin/api/employees/{employee_id}` is HR-only; a recruiter or manager answers `403`. It
marks the employee `left`, completes their active runs, deletes their question rows, deletes every
outbox message for their chat (pending reminders and replies included), and strips the employee's
own words from their audit rows. The employee row and the audit skeleton stay so counts remain
traceable. A repeated call answers `200` with zero counts. The response is:

```json
{
  "employee_id": "1001",
  "questions_deleted": 4,
  "messages_deleted": 2,
  "runs_closed": 1,
  "audit_redacted": 6
}
```

`DigestList`:

```json
{
  "items": [
    {
      "employee_id": "1001",
      "employee_name": "Анна Смирнова",
      "department": "Производство",
      "step_id": "week_two_survey",
      "level": "high",
      "reasons": ["конфликт с руководителем"],
      "tags": ["manager"],
      "quote": "руководитель не отвечает третий день",
      "at": "2026-10-22T15:30:00Z"
    }
  ],
  "since": "2026-10-16T09:00:00Z"
}
```

Only `high` and `medium` levels appear. `reasons` and `tags` are the classifier's short phrases.
`quote` is the employee's own words, truncated to 500 characters at write time and carried in the
`risk_assessed` audit event as `evidence`; it is `null` for a pure scale signal, which has no text.
A manager sees the same shape, scoped to one department.

`KnowledgeDocument`:

```json
{
  "id": "hr/leave-policy",
  "title": "Отпуска и отгулы",
  "type": "knowledge",
  "audience": ["all"],
  "owner": "hr",
  "valid_from": "2026-01-01",
  "valid_to": null,
  "updated_at": "2026-10-23T08:00:00Z"
}
```

`POST /admin/api/knowledge` takes `{"text": "<markdown with frontmatter>"}` and answers `201`:

```json
{"id": "hr/sport-compensation", "title": "Компенсация спорта", "chunks": 1}
```

The frontmatter is validated against `docs/contracts/doc.schema.json` before anything is written.
An invalid document answers `422` with the exact field, for example
`upload: owner: 'HR' does not match '^[a-z][a-z0-9_-]*$'`. Only `hr_admin` may upload; a recruiter
or manager answers `403`. A successful upload is audited as `knowledge_ingested` with the document
id, the chunk count, and the subject that made the change.

### Files

`POST /admin/api/knowledge/files` is `multipart/form-data` with two parts:

- `file`: a PDF or a PPTX, at most `EXTRACTION_MAX_UPLOAD_BYTES` (default 25 MiB);
- `metadata`: a JSON object with the document frontmatter (`id`, `title`, `type`, `status`,
  `owner`, `audience`, `valid_from`, optional `valid_to`), validated against
  [`doc.schema.json`](doc.schema.json) before anything is stored.

The response is `202 Accepted`, because recognition takes seconds per page and the request path
does not wait for it:

```json
{"content_hash": "5f2c...e1", "status": "queued"}
```

`content_hash` is the SHA-256 of the bytes. It is the identity of the file: uploading the same bytes
twice returns the same hash and queues no second job, so a recruiter can retry a flaky upload
without paying for recognition twice. The file itself is a `kb_files` row; nothing is written to
`knowledge/`, and nothing enters the corpus until extraction accepts it.

`GET /admin/api/knowledge/files/{content_hash}` answers the newest extraction record for that file,
whichever profile produced it:

```json
{
  "content_hash": "5f2c...e1",
  "status": "indexed",
  "reason": null,
  "engine": "pdfium",
  "route": "native_text",
  "pages": 6,
  "min_confidence": 1.0,
  "document_id": "hr/uploaded-regulation"
}
```

`status` is `indexed` or `rejected`. `route` is `native_text`, `ocr`, or `rejected`. A rejected file
carries `reason` — `low_confidence`, `low_dpi`, `blurry`, `encrypted`, `no_pages`,
`unsupported`, `unreadable`, `too_many_pages`, `too_short`, or `empty` — and `document_id` stays
null. Before the worker has run, this endpoint answers `404`: the cabinet shows "queued", never a
guess.

The status is the extraction's, not the file's: after a profile change the same file can hold one
record per profile, and this endpoint reports the latest one.

## Errors

FastAPI's default shape: `{"detail": "..."}` with `401`, `403`, `404`, or `422` for a bad query.
The cabinet shows the detail text and never guesses from the status code alone.

## Rules

- Mutations are limited to the two knowledge uploads and the question resolution above. The cabinet
  never talks to MAX directly: every outbound message is an outbox row.
- Only `hr_admin` may upload a file; a recruiter or manager answers `403`. A format other than PDF
  or PPTX answers `415`, an oversized file `413`, invalid metadata `422` with the exact field.
- Every answer attempt already writes an audit row and a question row; the cabinet does not
  assemble them from logs.
- Timestamps are UTC ISO 8601.
