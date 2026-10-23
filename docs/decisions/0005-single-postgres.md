# 0005: One Postgres for state, vectors, queue, and outbox

Status: accepted. Date: 2026-10-23.

## Context

The workload is hundreds of employees, tens of questions per hour, and one team of two to five
people. Every additional stateful service costs a day of setup, a failure mode, and a backup
policy.

## Decision

Postgres with `pgvector` holds run state, the job queue, the outbox, knowledge chunks, audit
rows, and vectors. Jobs use `SELECT … FOR UPDATE SKIP LOCKED`. Timers are outbox rows, not memory
timers.

## Consequences

- One backup, one migration path, one connection string.
- Vector search and lexical search filter in the same transaction as the ACL check.
- Throughput ceiling is a single primary; measured headroom is documented, not assumed.
- If the queue outgrows Postgres, the port stays and the implementation changes. The boundary is
  `ports.py`, so this is a later decision, not a rewrite.

## Alternatives

Redis for the queue — rejected: no durability for in-flight timers by default, plus a second
store. Dedicated vector database — rejected: the corpus is a few thousand chunks.
