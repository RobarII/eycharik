# 0014: The cabinet writes through the outbox

- Status: accepted
- Date: 2026-10-24
- Supersedes: nothing

## Context

The cabinet was read-only. A recruiter who answered a question in MAX had no way to close it, so
the queue filled with items nobody could remove, and the answer lived only in a messenger. A
leaver's transcript stayed in the database forever, and audit rows kept the raw question text.

Two questions had to be settled together:

1. How does a reply written in the cabinet reach the employee?
2. What does "the employee left" and "the data is old" mean for rows that mention a person?

## Decision

**A reply is an outbox row, written in the same transaction that closes the question.** The
`POST /admin/api/questions/{id}/resolve` handler validates the reply, sets `resolved_at`,
`resolved_by`, and `resolution`, appends a `messages` row, and writes `question_resolved` to the
audit log. The existing dispatcher delivers it with per-chat pacing and retries. The API never
calls MAX.

**Leaving is a soft delete plus an immediate purge.** `DELETE /admin/api/employees/{id}` (HR only)
sets `status='left'` and `left_at`, closes the active run, deletes the employee's question rows, and
redacts personal fields in the audit log. The employee row and the audit skeleton survive: the
numbers and the sequence of events stay, the person's words do not.

**Age is a scheduled purge.** The worker runs `RetentionPurger` hourly; the cron entrypoint runs it
once per tick. Questions older than `DATA_RETENTION_DAYS` (default 365) are deleted. Audit rows
older than the window keep their name, actor, and timestamps, but `evidence`, `quote`, `question`,
and `text` are replaced by null and `redacted: true`. The pass writes `retention_purged` with the
counts.

## Consequences

- A reply survives a crash between the API and MAX: the question is closed and the message is
  pending in one commit. Delivery is at-least-once.
- Two recruiters resolving the same question: the second gets `409`, not a duplicate message.
- The worker must be running for replies to leave the outbox. A down worker delays replies; it does
  not lose them.
- The resolved question text and the reply stay available to the cabinet until the retention window
  closes. This is deliberate: the next recruiter needs the context.
- Audit rows cannot be used to reconstruct a deleted employee transcript. This is a loss of
  forensic detail, accepted in exchange for not keeping personal data forever.
- `DATA_RETENTION_DAYS` is a policy knob, not a technical limit. Changing it does not rewrite
  history; the next pass applies the new cutoff.

## Alternatives rejected

- **Call MAX directly from the API.** Two failure domains in one request, no pacing, no retry, and a
  closed question whose reply was lost. The outbox already solves this.
- **Hard-delete the employee row.** Destroys the audit skeleton and the aggregate numbers, and makes
  a repeated `DELETE` indistinguishable from an unknown id.
- **Delete audit rows on retention.** Loses the record that an action happened. Redaction keeps the
  shape of the history without the personal content.
