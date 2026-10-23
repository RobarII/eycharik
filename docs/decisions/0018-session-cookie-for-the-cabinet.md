# 0018: The cabinet authenticates with an HttpOnly session cookie

- Status: accepted
- Date: 2026-10-25
- Supersedes: nothing (amends the authentication section of `docs/contracts/admin-api.md`)

## Context

The contract said "there is no session and no cookie", and the cabinet kept its bearer token in
`localStorage`. That choice had one property nobody wanted: any script on the page — a dependency,
a compromised CDN, an injected string — could read the token and take it home. The token cannot be
revoked by the browser, has no rotation, and one leaked value opens every employee the role can see.

The SPA is served from the same origin as `/admin/api`, so the token never needed to leave the
browser in a place script can reach.

## Decision

**The cabinet trades the token for an `HttpOnly` session cookie.**

`POST /admin/api/session` takes `{"token": "..."}` once, resolves it exactly like a bearer header
(same constant-time comparison, same expiry, same per-peer throttle), and answers `204` with:

```
Set-Cookie: onboarding_session=<token>; HttpOnly; SameSite=Strict; Path=/admin/api; Max-Age=43200
```

`Secure` is added whenever `ENVIRONMENT` is not `local`, so the plain-http docker demo still works.
`DELETE /admin/api/session` clears the cookie and is deliberately unauthenticated: signing out must
work for a token that just expired.

**The bearer header stays accepted.** curl, the server tests and a reverse proxy that injects the
header keep working. The header wins when both are present, so an explicit credential is never
silently overridden by a cookie.

**The token value is the cookie value.** A session is not a separate record with its own lifetime;
it is the same secret, held where script cannot read it. Revocation is the existing one: remove the
entry from `ADMIN_TOKENS` and redeploy. This keeps one source of truth and no new table.

## Consequences

- `localStorage` no longer holds a secret. An XSS bug can still act as the signed-in user for the
  length of the visit, but it cannot copy a credential off the machine.
- CSRF is controlled by `SameSite=Strict`: another origin cannot make the browser attach the cookie
  to a cross-site request. Same-origin script is already inside the trust boundary.
- `Path=/admin/api` keeps the cookie off `/healthz`, `/readyz` and `/metrics`.
- The cookie lasts 12 hours; the token's own expiry is still checked on every request. A short-lived
  token expires the session early, which is the intended failure mode.
- The cookie carries no `Domain`, so it is host-only. A second cabinet hostname needs its own login.
- Logging in is a `POST` with a body, so the token never appears in a URL, a `Referer`, or an access
  log line.

## Alternatives rejected

- **Keep the bearer token in `localStorage`.** Simplest, and one XSS away from a permanent leak.
- **Keep the token in memory only.** Survives nothing: every reload is a login, and two tabs cannot
  share a session.
- **A signed opaque session id with a server-side table.** Better revocation, but it adds a table, a
  cleanup job and a session store to a cabinet whose whole auth model is "the token is the identity".
  Revisit when a person needs several concurrent long-lived sessions.
- **`sessionStorage` instead of `localStorage`.** Still readable by script, and breaks the second tab.
