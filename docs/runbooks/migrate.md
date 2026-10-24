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

## A database from a feature branch

Two branches that both add a migration produce two histories, and the same change can be numbered
differently on each. A database stamped by one of them cannot be upgraded by the other:

```
ERROR [alembic.util.messaging] Can't locate revision identified by '0011_channel_address'
```

Here the branch added `channel_address` as `0011`; on `main` the same migration is `0014`, and
`0011`–`0013` are a bundled image column, an index state table and a question owner. Do not delete
rows from `alembic_version` and do not hand-edit the schema. Re-anchor the stamp to the last
revision both histories agree on and let alembic apply the rest:

```bash
# 1. What does the database claim, and what does this tree know? (the error above names the gap)
docker exec $PG psql -U onboarding -d $DB -tAc 'select version_num from alembic_version'
uv run alembic history | head

# 2. Before moving the stamp, diff the two migrations if the ids diverge:
#    if the bodies are identical, the later one is a no-op because it inspects the catalog first
diff <(sed -n '/^def upgrade/,$p' old_revision.py) <(sed -n '/^def upgrade/,$p' new_revision.py)

# 3. Re-anchor to the last common revision and upgrade. A migration that guards every step with
#    an inspector is safe to run on a schema that already has its columns.
docker exec $PG psql -U onboarding -d $DB -c \
  "update alembic_version set version_num='0010_messages_retention'"
uv run alembic upgrade head
docker exec $PG psql -U onboarding -d $DB -tAc 'select version_num from alembic_version'
```

Then prove the schema the code needs exists, not just the stamp:

```sql
select column_name from information_schema.columns
  where table_name = 'messages' and column_name in ('image', 'channel');
```

A worker started before this point fails on the first outbound lease with
`column messages.image does not exist` and keeps the row pending, so the symptom is silence, not a
crash loop.

## Rollback

Not supported in production. If a migration is wrong, ship a corrective migration and record the
incident.
