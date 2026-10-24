"""Admin authentication: bearer token or session cookie to (role, subject).

Every request proves itself. A token is compared in constant time, may carry an expiry date, and a
peer that fails repeatedly is throttled before it can walk a dictionary.

The cabinet trades the token for a session cookie through ``POST /admin/api/session``. The cookie
is ``HttpOnly`` and ``SameSite=Strict``, so script on the page cannot read it and another origin
cannot make the browser attach it. The bearer header stays accepted: curl, the tests and a reverse
proxy that injects the header keep working.

The principal's role decides the capability list the cabinet renders from, so the client never has
to guess what the server will allow.
"""

from __future__ import annotations

import hmac
import ipaddress
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Header, HTTPException, Request, status

from onboarding.api.ratelimit import auth_failures

SESSION_COOKIE = "onboarding_session"
SESSION_PATH = "/admin/api"
# The cookie outlives one working day; the token's own expiry is still enforced per request.
SESSION_TTL = timedelta(hours=12)

# The single source of truth for what a role may do. The cabinet renders from this list; every
# endpoint still enforces its own rule, so a forged capability changes nothing but the UI.
CAPABILITIES: dict[str, tuple[str, ...]] = {
    "recruiter": (
        "runs.read",
        "questions.read",
        "questions.resolve",
        "questions.assign",
        "knowledge.read",
        "analytics.read",
    ),
    "manager": (
        "runs.read",
        "questions.read",
        "questions.resolve",
        "questions.assign",
        "knowledge.read",
        "analytics.read",
    ),
    "hr_admin": (
        "runs.read",
        "questions.read",
        "questions.resolve",
        "questions.assign",
        "knowledge.read",
        "knowledge.write",
        "employees.offboard",
        "analytics.read",
    ),
}


@dataclass(frozen=True, slots=True)
class AdminPrincipal:
    role: str
    subject: str
    expires_at: datetime | None = None

    @property
    def is_hr(self) -> bool:
        return self.role == "hr_admin"

    @property
    def is_manager(self) -> bool:
        """A department head sees one department and nothing else."""
        return self.role == "manager"

    @property
    def capabilities(self) -> tuple[str, ...]:
        """An unknown role gets no capabilities: the default is closed, not open."""
        return CAPABILITIES.get(self.role, ())


def _peer(request: Request) -> str:
    """The rate-limit key.

    ``X-Real-IP`` is trusted only when the TCP peer is loopback or private, which is the docker
    network the cabinet's nginx lives on. A direct public caller cannot spoof its way out of the
    limit.
    """
    peer = request.client.host if request.client else ""
    forwarded = request.headers.get("X-Real-IP", "").strip()
    if not forwarded or not peer:
        return peer or "unknown"
    try:
        if ipaddress.ip_address(peer).is_private or ipaddress.ip_address(peer).is_loopback:
            return str(ipaddress.ip_address(forwarded))
    except ValueError:
        return peer
    return peer


async def authenticate(request: Request, presented: str | None) -> AdminPrincipal:
    """Resolve one presented secret, counting failures against the peer.

    Both the bearer header and the session cookie lead here, so an expired or unknown secret is
    throttled and rejected identically however it arrived.
    """
    peer = _peer(request)
    if auth_failures.blocked(peer):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too many failed attempts")

    if not presented:
        auth_failures.fail(peer)
        raise _unauthorized("token_missing", "bearer token or session required")

    container = request.app.state.container
    for token, spec in container.settings.admin_principals.items():
        if hmac.compare_digest(presented, token):
            if spec.expires_at is not None and container.clock.now() >= spec.expires_at:
                auth_failures.fail(peer)
                raise _unauthorized("token_expired", "token expired")
            auth_failures.succeed(peer)
            return AdminPrincipal(
                role=spec.role, subject=spec.subject, expires_at=spec.expires_at
            )
    auth_failures.fail(peer)
    raise _unauthorized("token_unknown", "unknown token")


async def current_admin(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> AdminPrincipal:
    """The bearer header wins; the cabinet's session cookie is the fallback."""
    presented: str | None = None
    if authorization is not None and authorization.startswith("Bearer "):
        presented = authorization.removeprefix("Bearer ").strip()
    if not presented:
        presented = request.cookies.get(SESSION_COOKIE)
    return await authenticate(request, presented)


def _unauthorized(code: str, message: str) -> HTTPException:
    """401 with a code the cabinet can act on: a missing token and an expired one differ."""
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED, {"code": code, "message": message}
    )


def require_hr(principal: AdminPrincipal) -> None:
    if not principal.is_hr:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "hr role required")
