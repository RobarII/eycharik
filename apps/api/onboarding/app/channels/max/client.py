"""HTTP client for the MAX Bot API.

Only the documented endpoints are called; the contract and its sources live in
``docs/contracts/max-api.md``. Messages are rate-limited per chat because MAX accepts at most two
per second to one dialog.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import SecretStr

from onboarding.app.channels.max.render import to_attachments
from onboarding.core.models import Address, Channel, Keyboard
from onboarding.ports import (
    ChannelRejectedError,
    ChannelUnavailableError,
    Messaging,
    OutboundMessage,
)


class MaxError(RuntimeError):
    """Base class for MAX API failures."""


class MaxUnavailableError(ChannelUnavailableError):
    """Transport failure or a 5xx: worth retrying later."""


class MaxRejectedError(ChannelRejectedError):
    """4xx: the request is wrong and a retry will not help."""


@dataclass(frozen=True, slots=True)
class Subscription:
    url: str
    update_types: tuple[str, ...]
    secret: SecretStr


class MaxClient(Messaging):
    channel = Channel.MAX

    def __init__(
        self,
        *,
        base_url: str,
        token: SecretStr,
        client: httpx.AsyncClient,
        messages_per_second: float = 2.0,
    ) -> None:
        if messages_per_second <= 0:
            raise ValueError("messages_per_second must be positive")
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._client = client
        self._min_interval = 1.0 / messages_per_second
        self._last_sent: dict[int, float] = {}
        self._lock = asyncio.Lock()

    async def send(self, message: OutboundMessage) -> str:
        await self._pace(int(message.address.chat_id))
        body: dict[str, Any] = {"text": message.text}
        attachments = to_attachments(message.keyboard)
        if attachments:
            body["attachments"] = attachments
        if message.reply_to is not None:
            body["link"] = {"type": "reply", "mid": message.reply_to}
        payload = await self._request(
            "POST",
            "/messages",
            params={"chat_id": int(message.address.chat_id)},
            json=body,
        )
        mid = _get(payload, "message", "body", "mid")
        if not isinstance(mid, str) or not mid:
            raise MaxError("MAX response has no message.body.mid")
        return mid

    async def edit(
        self, address: Address, message_id: str, text: str, keyboard: Keyboard = ()
    ) -> None:
        del address
        body: dict[str, Any] = {"text": text}
        attachments = to_attachments(keyboard)
        if attachments:
            body["attachments"] = attachments
        await self._request("PUT", f"/messages/{message_id}", json=body)

    async def me(self) -> dict[str, Any]:
        return await self._request("GET", "/me")

    async def subscribe(self, subscription: Subscription) -> None:
        await self._request(
            "POST",
            "/subscriptions",
            json={
                "url": subscription.url,
                "update_types": list(subscription.update_types),
                "secret": subscription.secret.get_secret_value(),
            },
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = await self._client.request(
                method,
                f"{self._base_url}{path}",
                params=params,
                json=json,
                headers={
                    "Authorization": self._token.get_secret_value(),
                    "Content-Type": "application/json",
                },
            )
        except (httpx.TimeoutException, httpx.TransportError) as error:
            raise MaxUnavailableError(f"{type(error).__name__}: {error}") from None
        if response.status_code >= 500:
            raise MaxUnavailableError(f"MAX answered HTTP {response.status_code}")
        if response.status_code >= 400:
            raise MaxRejectedError(f"MAX answered HTTP {response.status_code}")
        if not response.content:
            return {}
        body = response.json()
        return body if isinstance(body, dict) else {}

    async def _pace(self, chat_id: int) -> None:
        async with self._lock:
            last = self._last_sent.get(chat_id, 0.0)
            wait = self._min_interval - (time.monotonic() - last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_sent[chat_id] = time.monotonic()


def _get(payload: dict[str, Any], *path: str) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def update_types() -> tuple[str, ...]:
    return ("message_created", "message_callback", "bot_started", "bot_stopped")


__all__ = [
    "MaxClient",
    "MaxError",
    "MaxRejectedError",
    "MaxUnavailableError",
    "Subscription",
    "update_types",
]
