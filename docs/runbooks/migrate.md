# Runbook: database migration

## Rules

- Migrations are forward-only. A mistake is fixed by the next migration.
- A migration that rewrites a large table is split: add, backfill, then switch reads.
- Every migration is tested against a fresh database and against a copy of staging data.

## Steps

1. Write the migration next to the model change, in `apps/api/onboarding/app/db/migrations/`.
2. Run `alembic upgrade head` against a scratch database.
3. Run `pytest -m integration` against that database.
4. Run the backfill as a separate command, never inside the migration, when the table is large.
5. Deploy the worker before the gateway if the migration changes a column the gateway reads.

## Verification

```bash
alembic current
alembic check          # no pending model changes
```

## Rollback

Not supported in production. If a migration is wrong, ship a corrective migration and record the
incident.
