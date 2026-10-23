# Runbook: deploy

## Preconditions

- `main` is green: `make check` and `make eval` pass.
- A migration exists for every schema change, and it is forward-only.
- `MAX_CA_BUNDLE`, `MAX_BOT_TOKEN`, `MAX_WEBHOOK_SECRET`, `LLM_*`, and `DATABASE_URL` are set in
  the environment, never in the image.

## Steps

1. Build and tag: `docker build -f infra/Dockerfile -t onboarding-api:<sha> .`
2. Apply migrations: `make migrate` (runs `alembic upgrade head` once, not per replica).
3. Start the worker first, then the gateway. The gateway may accept traffic while the worker is
   down; jobs accumulate but nothing is lost.
4. Smoke test: `curl -f https://$HOST/readyz`, then send `/start` from a test MAX account.
5. Register or refresh the webhook:

```bash
curl -X POST "https://platform-api2.max.ru/subscriptions" \
  -H "Authorization: $MAX_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://'"$HOST"'/webhook/max",
       "update_types":["message_created","message_callback","bot_started","bot_stopped"],
       "secret":"'"$MAX_WEBHOOK_SECRET"'"}'
```

6. Check the first minute of `gateway_requests_total` and the first `answer_completed` trace.

## Rollback

Deploy the previous image tag. Do not roll back migrations in production; write a forward fix.
The webhook subscription stays valid because the URL does not change.

## Post-deploy

Record the version and the smoke result in `docs/measurements/` if the deploy changes a measured
number. If something broke, write `docs/incidents/` the same day.
