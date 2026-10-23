# Runbook: webhooks rejected or not arriving

## Symptoms

- MAX reports delivery failures; `events` stops growing.
- Every delivery answers `401`.
- MAX unsubscribes after 8 hours of failures.

## Checks, in order

1. **Reachability**: `curl -v https://$HOST/webhook/max` must complete a TLS handshake with a trusted
   chain, on port 443, with the URL host matching the certificate. A `401` from this curl is the
   correct answer: the route exists and rejected an unsigned request.
2. **Secret configuration**: an empty `MAX_WEBHOOK_SECRET` makes the route answer `503`. The
   header MAX sends is `X-Max-Bot-Api-Secret`; the route compares it in constant time. A rotated
   secret requires re-registering the subscription.
3. **Subscription**: re-run the `subscribe` command in [deploy.md](deploy.md). An old subscription
   pointing at a dead tunnel explains silence.
4. **Response time**: the route must answer `200` within 30 seconds. It performs two inserts and no
   model call. If p95 approaches the limit, the database is the suspect, not the bot.
5. **Body**: only `POST` with JSON. A proxy that buffers or rewrites the body is irrelevant to the
   secret check but breaks large payloads; bodies over 1 MB are rejected with `413`.

## Confirm the pipeline

```sql
select count(*) from events;
select status, count(*) from jobs group by status;
select * from audit_log order by created_at desc limit 20;
```

An `events` row without a `jobs` row means the transaction is not committing both; they share one
transaction, so this should be impossible and is a bug worth an incident.

## Recovery

Re-register the subscription, send `/start` from a test account, and confirm the three rows above.
