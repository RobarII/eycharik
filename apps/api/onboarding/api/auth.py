"""Admin authentication: bearer token to (role, subject).

There is no session and no cookie: the cabinet is a separate SPA talking to a JSON API, and every
request proves itself. Tokens are compared in constant time, may carry an expiry date, and a peer
that fails repeatedly is throttled before it can walk a dictionary.
"""

from __future__ import annotations

import hmac
import ipaddress
from dataclasses import dataclass
from typing import Annotated

from fastapi import Header, HTTPException, Request, status

from onboarding.api.ratelimit import auth_failures


@dataclass(frozen=True, slots=True)
class AdminPrincipal:
    role: str
    subject: str

    @property
    def is_hr(self) -> bool:
        return self.role == "hr_admin"

    @property
    def is_manager(self) -> bool:
        """A department head sees one department and nothing else."""
        return self.role == "manager"


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


async def current_admin(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> AdminPrincipal:
    peer = _peer(request)
    if auth_failures.blocked(peer):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too many failed attempts")

    if authorization is None or not authorization.startswith("Bearer "):
        auth_failures.fail(peer)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bearer token required")
    presented = authorization.removeprefix("Bearer ").strip()
    if not presented:
        auth_failures.fail(peer)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bearer token required")

    container = request.app.state.container
    for token, spec in container.settings.admin_principals.items():
        if hmac.compare_digest(presented, token):
            if spec.expires_at is not None and container.clock.now() >= spec.expires_at:
                auth_failures.fail(peer)
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token expired")
            auth_failures.succeed(peer)
            return AdminPrincipal(role=spec.role, subject=spec.subject)
    auth_failures.fail(peer)
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unknown token")


def require_hr(principal: AdminPrincipal) -> None:
    if not principal.is_hr:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "hr role required")
