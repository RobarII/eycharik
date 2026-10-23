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

There is no session and no cookie. Tokens are compared in constant time. An unknown, missing or
expired token answers `401`; ten failed attempts from one peer within a minute answer `429` for the
next minute. A run outside the caller's scope answers `404`, so the existence of another
recruiter's employee is not disclosed.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/admin/api/runs?limit=50` | active and completed runs, newest activity first |
| `GET` | `/admin/api/runs/{run_id}` | one run: step, step text, audit events, recent questions |
| `GET` | `/admin/api/questions?status=unanswered&limit=50` | questions by status: `unanswered`, `answered`, `all` |
| `POST` | `/admin/api/questions/{question_id}/resolve` | answer an escalated question in MAX and close it |
| `DELETE` | `/admin/api/employees/{employee_id}` | HR offboards an employee: stops the run, deletes the transcript |
| `GET` | `/admin/api/analytics/overview` | seven-day counts: runs, risk levels, unanswered questions, top risk tags |
| `GET` | `/admin/api/digest/weekly?days=7` | signals that deserve a human, one row per employee and step |
| `GET` | `/admin/api/knowledge` | active knowledge documents, newest first |
| `POST` | `/admin/api/knowledge` | HR uploads one markdown document with frontmatter; indexed in the request |
| `GET` | `/healthz`, `/readyz` | liveness and readiness, no auth |

`limit` is bounded to `1..200`. There is no cursor pagination yet: the cabinet asks for the newest
50 and the dataset is one cohort of hires. If a cohort outgrows that, add a cursor before raising
the cap.

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
  "status": "active"
}
```

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
  "resolved_by": null
}
```

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
marks the employee `left`, completes their active runs, deletes their question rows, and strips the
employee's own words from their audit rows. The employee row and the audit skeleton stay so counts
remain traceable. A repeated call answers `200` with zero counts. The response is:

```json
{
  "employee_id": "1001",
  "questions_deleted": 4,
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

## Errors

FastAPI's default shape: `{"detail": "..."}` with `401`, `403`, `404`, or `422` for a bad query.
The cabinet shows the detail text and never guesses from the status code alone.

## Rules

- Mutations are limited to the knowledge upload and the question resolution above. The cabinet
  never talks to MAX directly: every outbound message is an outbox row.
- Every answer attempt already writes an audit row and a question row; the cabinet does not
  assemble them from logs.
- Timestamps are UTC ISO 8601.
