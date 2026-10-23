# Runbook: retention and offboarding

What the system keeps, for how long, and how to check that a purge happened.

## What is covered

| Data | Where | Retention |
|---|---|---|
| Escalated questions and answers | `questions` | `DATA_RETENTION_DAYS` after `asked_at` |
| Replies written in the cabinet | `questions.resolution`, `messages` outbox | same as the question |
| Personal fields in the audit log (`evidence`, `quote`, `question`, `text`) | `audit_log.fields` | replaced by null after `DATA_RETENTION_DAYS`; the row stays |
| Runs, risk signals, jobs, events | `runs`, `risk_*`, `jobs`, `events` | not purged; they carry ids, not free text |
| Knowledge documents | `kb_*` | not personal data; versioned by `valid_from` / `valid_to` |

`DATA_RETENTION_DAYS` defaults to 365, must be at least 1, and is read at process start. It is a
policy value: change it in the deployment environment, not in the database.

## Offboarding an employee

HR only. The call is idempotent: a second `DELETE` returns zero counts and `200`.

```bash
curl -X DELETE "https://$HOST/admin/api/employees/$EMPLOYEE_ID" \
  -H "Authorization: Bearer $HR_TOKEN"
```

Expected response: `{"employee_id": "...", "runs_closed": 1, "questions_deleted": 3,
"audit_rows_redacted": 7}`. The employee disappears from the directory and from every scoped list;
the row remains with `status='left'` and `left_at`.

## How the scheduled purge runs

- Worker: once an hour, next to the scheduler tick.
- Cron entrypoint (`python -m onboarding.scheduler`): once per tick, after the outbox drain.
- Each pass writes `retention_purged` to `audit_log` with `questions` and `audit_rows` counts.

A pass is safe to re-run: it deletes by cutoff and redaction only touches fields that are still
present.

## Verify

```sql
-- oldest retained question; should be newer than now() - DATA_RETENTION_DAYS
select min(asked_at) from questions;

-- audit rows still carrying personal fields past the window; should return 0
select count(*) from audit_log
where created_at < now() - interval '365 days'
  and fields ?| array['evidence', 'quote', 'question', 'text'];

-- recent purge passes
select created_at, fields
from audit_log
where name = 'retention_purged'
order by created_at desc
limit 5;
```

If the first query is older than the window, the worker is not running or the pass is failing; read
the worker log for `retention` and the `retention_purged` rows. If the second is non-zero, a field
name was added to an audit event without being added to `PERSONAL_AUDIT_KEYS` in
`apps/api/onboarding/core/retention.py`.

## Notes

- This runbook describes the mechanism, not the legal sufficiency of the window. The retention
  period is owned by the company's data protection policy; 365 days is a placeholder that must be
  confirmed before a production deployment.
- Offboarding is immediate and irreversible. Export anything the policy requires before calling
  `DELETE`.
