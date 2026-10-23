# 0002: The webhook acknowledges before it works

Status: accepted. Date: 2026-10-23.

## Context

MAX acknowledges a webhook with any response within 30 seconds, retries up to 10 times with an
exponential schedule, and unsubscribes after 8 hours without a success. An answer path involves
retrieval and a model call: p95 is seconds, and a provider incident makes it tens of seconds.

## Decision

The gateway validates the request, writes a `processed_events` row and a `jobs` row in one
transaction, and returns `200`. Work happens in the worker. Idempotency is a unique index on
`event_id`, not a cache.

## Consequences

- Webhook latency is independent of the model.
- At-least-once delivery becomes exactly-once processing at the database boundary.
- Two extra tables and a worker loop exist.
- A duplicate delivery is a single failed insert, not a duplicate answer to a newcomer.

## Alternatives

Synchronous handling — rejected: a slow model turns into MAX retries and duplicate messages.
External broker (RabbitMQ, Redis Streams) — rejected: another stateful service for a workload of
hundreds of messages per day, see [0005](0005-single-postgres.md).
