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
| `manager` | employees of one department: the token's subject is the department name |
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
| `GET` | `/admin/api/analytics/overview` | seven-day counts: runs, risk levels, unanswered questions, top risk tags |
| `GET` | `/admin/api/digest/weekly?days=7` | signals that deserve a human, one row per employee and step |
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

`AnalyticsOverview`:

```json
{
  "active_runs": 12,
  "completed_runs": 4,
  "high_risk": 2,
  "medium_risk": 5,
  "unanswered_questions": 3,
  "top_tags": [{"tag": "access", "count": 4}, {"tag": "manager", "count": 2}],
  "since": "2026-10-16T09:00:00Z"
}
```

The counts cover the window that starts at `since` and come from the audit log, not from a
materialised table: the cabinet is read-only, and a wrong number must be traceable to events.

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
      "at": "2026-10-22T15:30:00Z"
    }
  ],
  "since": "2026-10-16T09:00:00Z"
}
```

Only `high` and `medium` levels appear. `reasons` and `tags` are the classifier's short phrases,
never the full answer text: the digest is a list of leads, not a transcript. A manager sees the
same shape, scoped to one department.

## Errors

FastAPI's default shape: `{"detail": "..."}` with `401`, `403`, `404`, or `422` for a bad query.
The cabinet shows the detail text and never guesses from the status code alone.

## Rules

- The API is read-only today. Manual messages and escalation resolution are the next mutations.
- Every answer attempt already writes an audit row and a question row; the cabinet does not
  assemble them from logs.
- Timestamps are UTC ISO 8601.
