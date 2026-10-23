# Admin API contract

The recruiter cabinet reads this API. The bot never calls it.

## Authentication

`Authorization: Bearer <token>`. Tokens are configured in `ADMIN_TOKENS` as
`token:role:subject` entries:

```
ADMIN_TOKENS=dev-recruiter-token:recruiter:rec-1,dev-hr-token:hr_admin:hr-1
```

| Role | Scope |
|---|---|
| `recruiter` | employees whose `recruiter_id` equals the token's subject |
| `hr_admin` | every employee and every question |

There is no session and no cookie. Tokens are compared in constant time. An unknown or missing
token answers `401`; a run outside the caller's scope answers `404`, so the existence of another
recruiter's employee is not disclosed.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/admin/api/runs?limit=50` | active and completed runs, newest activity first |
| `GET` | `/admin/api/runs/{run_id}` | one run: step, step text, audit events, recent questions |
| `GET` | `/admin/api/questions?status=unanswered&limit=50` | questions by status: `unanswered`, `answered`, `all` |
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
  "step_number": 4,
  "steps_total": 6,
  "entered_at": "2026-10-20T09:00:00Z",
  "status": "active"
}
```

`RunDetail` extends `RunSummary` with `scenario`, `scenario_version`, `step_message`, `events`,
and `questions`. Its questions are only that employee's, limited to the newest 20.

`Question`:

```json
{
  "employee_id": "1001",
  "employee_name": "Анна Смирнова",
  "text": "Сколько дней отпуска?",
  "answered": false,
  "reason": "no_sources",
  "citations": [],
  "asked_at": "2026-10-23T07:12:00Z"
}
```

## Errors

FastAPI's default shape: `{"detail": "..."}` with `401`, `403`, `404`, or `422` for a bad query.
The cabinet shows the detail text and never guesses from the status code alone.

## Rules

- The API is read-only today. Manual messages and escalation resolution are the next mutations.
- Every answer attempt already writes an audit row and a question row; the cabinet does not
  assemble them from logs.
- Timestamps are UTC ISO 8601.
