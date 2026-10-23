"""Admin authentication: bearer token to (role, subject).

There is no session and no cookie: the cabinet is a separate SPA talking to a JSON API, and every
request proves itself. Tokens are compared in constant time.
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Annotated

from fastapi import Header, HTTPException, Request, status


@dataclass(frozen=True, slots=True)
class AdminPrincipal:
    role: str
    subject: str

    @property
    def is_hr(self) -> bool:
        return self.role == "hr_admin"


async def current_admin(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> AdminPrincipal:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bearer token required")
    presented = authorization.removeprefix("Bearer ").strip()
    principals = request.app.state.container.settings.admin_principals
    for token, (role, subject) in principals.items():
        if hmac.compare_digest(presented, token):
            return AdminPrincipal(role=role, subject=subject)
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unknown token")


def require_hr(principal: AdminPrincipal) -> None:
    if not principal.is_hr:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "hr role required")
