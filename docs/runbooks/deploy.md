# Runbook: deploy

## Preconditions

- `make check` is green. `make eval-retrieval` is green; `make eval` is green if a provider is
  reachable.
- Every schema change has a migration under `apps/api/onboarding/migrations/versions/`.
- These are set in the environment, never baked into the image: `DATABASE_URL`, `MAX_BOT_TOKEN`,
  `MAX_WEBHOOK_SECRET`, `LLM_API_KEY`, `ADMIN_TOKENS`, `DATA_RETENTION_DAYS`, and `MAX_CA_BUNDLE`
  when the Mincifry CA is not in the system store.
- The public hostname terminates TLS on port 443. MAX rejects anything else.

## Steps

1. Build and tag the single image:

   ```bash
   docker build -t onboarding:<sha> .
   ```

2. Apply migrations once, before any new process starts:

   ```bash
   docker run --rm --env-file .env onboarding:<sha> alembic upgrade head
   ```

3. Start the worker before the API. The API accepts webhooks while the worker is down; jobs wait
   in `jobs` and nothing is lost.

   ```bash
   docker compose up -d worker api
   ```

4. Smoke test: `curl -f https://$HOST/healthz` and `curl -f https://$HOST/readyz`. Readiness checks
   the database only; the model is not on the request path.

5. Register the subscription with the secret MAX must echo back:

   ```bash
   uv run python -m onboarding.cli subscribe \
     --url "https://$HOST/webhook/max" \
     --types message_created,bot_started
   ```

   Re-running replaces the subscription for this bot. Tunnels change hostnames; re-register after
   every tunnel restart.

6. Send `/start` from a test account. Expect: an `events` row, a `jobs` row that reaches `done`, an
   outbox row that reaches `sent`, and one welcome message in MAX.

## Verification queries

```sql
select status, count(*) from jobs group by status;
select status, count(*) from messages group by status;
select name, count(*) from audit_log group by name order by 2 desc;
select count(*) filter (where resolved_at is not null) as resolved, count(*) from questions;
```

`messages` rows stuck in `pending` mean the dispatcher or the MAX API is failing; read
`last_error`.

## Rollback

Deploy the previous image tag. Do not roll back migrations in production; ship a forward fix. The
subscription stays valid because the URL does not change.

## Post-deploy

Record the version and the smoke result in `docs/measurements/` if the deploy changes a measured
number. If something broke, write `docs/incidents/` the same day.
