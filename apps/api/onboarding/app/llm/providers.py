"""Provider adapters: what to call and how to authenticate.

Both providers speak the OpenAI chat-completions dialect. The difference is authentication, the
base URL and the envelope, so a provider is a small object that produces a request — URL, headers,
body — and never a second gateway.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

import httpx
from pydantic import SecretStr


class ProviderError(RuntimeError):
    """The provider could not prepare a request (for example, an OAuth failure)."""


@dataclass(frozen=True, slots=True)
class PreparedRequest:
    url: str
    headers: dict[str, str]
    body: dict[str, object]


class Provider(Protocol):
    async def prepare(
        self, client: httpx.AsyncClient, body: dict[str, object]
    ) -> PreparedRequest: ...


@dataclass(frozen=True, slots=True)
class OpenAICompatibleProvider:
    base_url: str
    api_key: SecretStr
    extra_headers: Mapping[str, str] = field(default_factory=dict)

    async def prepare(
        self, client: httpx.AsyncClient, body: dict[str, object]
    ) -> PreparedRequest:
        del client
        return PreparedRequest(
            url=f"{self.base_url.rstrip('/')}/chat/completions",
            headers={
                **self.extra_headers,
                "Authorization": f"Bearer {self.api_key.get_secret_value()}",
                "Content-Type": "application/json",
            },
            body=body,
        )


@dataclass(slots=True)
class GigaChatProvider:
    """GigaChat needs an OAuth token; it expires, so it is cached with a safety margin."""

    base_url: str
    auth_key: SecretStr
    oauth_url: str
    scope: str = "GIGACHAT_API_PERS"
    refresh_margin_s: float = 60.0
    _token: str | None = field(default=None, init=False)
    _expires_at: float = field(default=0.0, init=False)

    async def prepare(
        self, client: httpx.AsyncClient, body: dict[str, object]
    ) -> PreparedRequest:
        return PreparedRequest(
            url=f"{self.base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {await self.authorization(client)}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            body=body,
        )

    async def authorization(self, client: httpx.AsyncClient) -> str:
        """Bearer token for any endpoint, refreshed with a safety margin."""
        if self._token is None or time.monotonic() >= self._expires_at - self.refresh_margin_s:
            await self._refresh(client)
        assert self._token is not None
        return self._token

    async def _refresh(self, client: httpx.AsyncClient) -> None:
        try:
            response = await client.post(
                self.oauth_url,
                headers={
                    "Authorization": f"Basic {self.auth_key.get_secret_value()}",
                    "RqUID": _request_id(),
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
                data={"scope": self.scope},
            )
        except httpx.HTTPError as error:
            raise ProviderError(f"gigachat oauth failed: {error}") from None
        if response.status_code >= 400:
            raise ProviderError(f"gigachat oauth answered {response.status_code}")
        payload = response.json()
        token = payload.get("access_token")
        expires_at = payload.get("expires_at")
        if not isinstance(token, str) or not isinstance(expires_at, int | float):
            raise ProviderError("gigachat oauth response is missing access_token or expires_at")
        self._token = token
        self._expires_at = float(expires_at) / 1000.0


def _request_id() -> str:
    return str(uuid.uuid4())
