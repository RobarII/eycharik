# Admin API contract

The recruiter cockpit reads this API. The bot never calls it. Authentication is a bearer token
issued by the platform SSO; the token carries `sub`, `role`, and `recruiter_id`.

## Authorisation

| Role | Scope |
|---|---|
| `recruiter` | only employees whose `recruiter_id` matches the token |
| `hr_admin` | all employees, all scenarios, knowledge management |
| `employee` | no admin access |

A request outside the scope answers `404`, not `403`: the existence of another recruiter's
employee is not disclosed.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/admin/employees?status=active&cursor=…` | paginated runs with step, progress, last activity |
| `GET` | `/admin/employees/{employee_id}` | one run: steps, events, escalations, transcript pointers |
| `POST` | `/admin/employees/{employee_id}/messages` | send a manual message through the bot |
| `POST` | `/admin/employees/{employee_id}/escalations/{id}/resolve` | close an escalation with a note |
| `GET` | `/admin/scenarios` | scenario versions, active flag |
| `GET` | `/admin/metrics/summary?from=&to=` | deflection, escalation rate, median time per step |
| `GET` | `/healthz`, `/readyz` | liveness and readiness (no auth inside the cluster) |

## Shapes

`EmployeeSummary`:

```json
{
  "employee_id": "uuid",
  "full_name": "Иванов Иван",
  "department": "ИТ",
  "scenario_id": "onboarding_default",
  "scenario_version": 3,
  "current_step": "collect_documents",
  "started_at": "2026-10-20T09:00:00Z",
  "last_activity_at": "2026-10-23T07:12:00Z",
  "progress": 0.4,
  "open_escalations": 1
}
```

Errors are RFC 9457 problem details:

```json
{"type": "about:blank", "title": "not_found", "status": 404, "detail": "employee not found"}
```

## Rules

- The API is read-mostly. Mutations are limited to messages, escalations, and knowledge status.
- Every mutation writes an audit row with the actor, the target, and the before/after.
- Listing is cursor-based; no offset pagination, no unbounded responses.
- Timestamps are UTC ISO 8601 with `Z`.
