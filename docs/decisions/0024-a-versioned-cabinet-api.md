# 0024: The cabinet API has a version in its path

- Status: accepted
- Date: 2026-10-24

## Context

The cabinet and the API are separate processes in separate repositories-in-spirit: the cabinet is a
static bundle in front of an nginx, the API is the only thing that knows what a run is. They ship
on different schedules, and a stale bundle is not an incident the deploy can prevent — a browser
tab can live for days.

The API grew under `/admin/api` with no version marker. Every one of the endpoints in
`docs/contracts/admin-api.md` is load-bearing for that stale bundle: renaming a field, dropping a
query parameter, or turning `total` into an estimate breaks a page in a tab nobody can reload.

The usual mitigations are worse than the problem. Additive-only discipline is unenforceable across
a year of changes, and a client capability probe (`GET /me` already carries one) tells the client
what it may *do*, not what shape the answer has.

## Decision

**Every cabinet route lives under `/admin/api/v1`. An incompatible change is a new prefix, not an
edit of this one.**

Both prefixes answer for one release. The unversioned `/admin/api` alias exists so a bundle that
has not shipped yet keeps working, and it is deliberately `include_in_schema=False`: it is a
compatibility window, not a second contract. It is removed in the release after the cabinet's
`api.ts` has pointed at `/admin/api/v1` everywhere.

The version covers the wire format of the cabinet API only. `/webhook/{channel}` is versioned by
the messenger's own API, `/healthz` and `/readyz` are infrastructure, and neither is part of this
promise.

## Consequences

- A field may be removed, renamed, or given a different type in `v2` while `v1` keeps its shape.
- The OpenAPI document describes `v1` only, so a generated client never sees the alias.
- The session cookie path stays `/admin/api`, which covers both prefixes. Authentication is not
  versioned: a `v2` client trades the same token the same way.
- A route that exists in both prefixes is logged by its template, so the metrics split
  `/admin/api/v1/runs` from `/admin/api/runs` while the alias lives. That is intentional: it makes
  the day the alias stops being used visible in Grafana, not just in a changelog.
- The legacy alias is one line in `api/app.py`. Removing it is a deliberate commit, not a
  side effect of a refactor.

## Alternatives rejected

- **A version in a header (`Accept: application/vnd.onboarding.v2+json`).** Prettier, but a proxy a
  client forgets to configure silently gets `v1`, and `curl` in a runbook shows nothing about which
  contract the output obeys.
- **A query parameter (`?v=2`).** Same silence, plus it invites per-endpoint versions.
- **Never breaking the contract.** Costs a permanent compatibility layer in every response model,
  for a client that the repository can see is stale.
- **A separate host (`api-v2.example`).** Buys nothing the path does not, and costs a DNS record,
  a certificate, and a deploy per version.
