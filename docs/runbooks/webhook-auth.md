# Runbook: webhooks rejected or not arriving

## Symptoms

- MAX reports delivery failures; no `gateway_requests_total`.
- `401` for every delivery.
- The bot unsubscribes after 8 hours of failures.

## Checks, in order

1. **Reachability**: `curl -v https://$HOST/webhook/max` must complete a TLS handshake with a
   trusted chain, on port 443, with the URL host matching the certificate.
2. **Secret**: the header is `X-Max-Bot-Api-Secret`; compare with `MAX_WEBHOOK_SECRET` in constant
   time. A rotated secret requires re-registering the subscription.
3. **Subscription**: `POST /subscriptions` with the current URL and `update_types`; an old
   subscription pointing at a dead tunnel explains silence.
4. **Response time**: the gateway must answer `200` within 30 seconds. If the worker is called
   inline, this is the bug.
5. **Method and body**: only `POST` with JSON; a proxy that buffers or rewrites the body breaks the
   signature.

## Recovery

Re-register the subscription (command in [deploy.md](deploy.md)), send `/start` from a test
account, and confirm one trace with `gateway_requests_total` and one `answer_completed`.

## Notes

Tunnels change hostnames. After every tunnel restart, the subscription must be re-registered —
production uses a stable hostname, never a temporary tunnel.
