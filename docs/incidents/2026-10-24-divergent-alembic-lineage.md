# 2026-10-24 — A database from the feature branch could not be upgraded by `main`

- **Severity**: `SEV3` — local and staging only; no customer traffic, no data lost
- **Duration**: `2026-10-24 12:05 – 12:35 UTC`
- **Impact**: the worker on `main` started and immediately failed every outbound lease. The API
  answered `200` to webhooks and the scenario advanced, so the visible symptom was silence in the
  messengers plus `pending` rows, not an error.
- **Detection**: the worker log, not a metric: `asyncpg.exceptions.UndefinedColumnError: column
  messages.image does not exist`

## Timeline

| Time (UTC) | Event |
|---|---|
| 12:05 | `feat/multi-channel` merged into `main`; the worker restarted from `main` |
| 12:08 | First outbound lease failed with `column messages.image does not exist` |
| 12:15 | `alembic upgrade head` refused: `Can't locate revision identified by '0011_channel_address'` |
| 12:25 | Migrations compared: same body, different ids (`0011_channel_address` on the branch, `0014_channel_address` on `main`) |
| 12:35 | Stamp re-anchored to `0010_messages_retention`, `upgrade head` applied `0011`–`0014`, worker restarted and delivered |

## Root cause

Two branches added a migration each and both numbered it from their own predecessor. The branch
named its channel migration `0011`; `main` had meanwhile used `0011`–`0013` for an image column, an
index state table and a question owner, and named the same channel migration `0014`. A database
stamped by the branch therefore points at a revision that does not exist in `main`'s history, and
alembic refuses to move at all — so none of `main`'s three missing migrations were applied either.

## Fix

`docs/runbooks/migrate.md`, section «A database from a feature branch». The two migrations were
compared before anything moved: identical bodies, and every step guards with an inspector, so the
later one is a no-op on a schema that already has its columns. The stamp was re-anchored to the last
common revision and `alembic upgrade head` applied the rest.

## Proof

`scripts/channel_smoke.py` completed 48/48 on the migrated database, both channel directions
(`docs/measurements/2026-10-24-cross-channel-move.md`), and the verification query in the runbook
returns both `image` and `channel`.

## Follow-ups

| Action | Owner | Due |
|---|---|---|
| Check `alembic heads` inside the pre-merge checklist, not after | whoever merges | next merge |
| Make the worker log a failing lease at `warning`, not only the traceback | platform | next sprint |
