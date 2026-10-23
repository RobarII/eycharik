# Runbook: database migration

## Rules

- Migrations are forward-only. A mistake is fixed by the next migration.
- The baseline `0001_initial` creates the schema from the SQLAlchemy metadata. Later migrations
  are hand-written and reviewed.
- A migration that rewrites a large table is split: add, backfill, then switch reads.
- `EMBED_DIM` is baked into the `kb_chunks.embedding` column and its HNSW index. Changing the
  embedding model is a migration, not a configuration change.

## Steps

1. Write the revision under `apps/api/onboarding/migrations/versions/`.
2. Apply it to a scratch database:

   ```bash
   DATABASE_URL=postgresql+asyncpg://onboarding:onboarding@localhost:5432/onboarding \
     uv run alembic upgrade head
   ```

3. Run the integration suite against that database:

   ```bash
   ONBOARDING_TEST_DATABASE=<same url> uv run pytest -m integration
   ```

4. Run a backfill as a separate command, never inside the migration, when the table is large.
5. Deploy the worker before the API if the migration changes a column the webhook reads.

## Verification

```bash
uv run alembic current
uv run alembic upgrade head --sql | head    # review the SQL before applying
```

`alembic check` is not used: the baseline reflects the metadata at its revision, and later
migrations legitimately drift from it until autogenerate is re-baselined.

## Rollback

Not supported in production. If a migration is wrong, ship a corrective migration and record the
incident.
