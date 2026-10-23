"""HTTP client for the MAX Bot API.

Only the documented endpoints are called; the contract and its sources live in
``docs/contracts/max-api.md``. Messages are rate-limited per chat because MAX accepts at most two
per second to one dialog.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from pydantic import SecretStr

from onboarding.app.channels.max.media import (
    asset_path,
    content_type,
    image_attachment,
    upload_token,
)
from onboarding.app.channels.max.render import to_attachments
from onboarding.core.models import Address, Channel, Keyboard
from onboarding.ports import (
    ChannelRejectedError,
    ChannelUnavailableError,
    Messaging,
    OutboundMessage,
)

ATTACHMENT_RETRY_SECONDS = (1.0, 2.0, 4.0)
ATTACHMENT_NOT_READY = "attachment.not.ready"


class MaxError(RuntimeError):
    """Base class for MAX API failures."""


class MaxUnavailableError(ChannelUnavailableError):
    """Transport failure or a 5xx: worth retrying later."""


class MaxRejectedError(ChannelRejectedError):
    """4xx: the request is wrong and a retry will not help."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


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
        assets_dir: Path | None = None,
    ) -> None:
        if messages_per_second <= 0:
            raise ValueError("messages_per_second must be positive")
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._client = client
        self._assets_dir = assets_dir
        self._min_interval = 1.0 / messages_per_second
        self._last_sent: dict[int, float] = {}
        self._lock = asyncio.Lock()
        self._image_tokens: dict[str, str] = {}
        self._image_lock = asyncio.Lock()

    async def send(self, message: OutboundMessage) -> str:
        body: dict[str, Any] = {"text": message.text}
        attachments = to_attachments(message.keyboard)
        if message.image is not None:
            token = await self._image_token(message.image)
            attachments.insert(0, image_attachment(token))
        if attachments:
            body["attachments"] = attachments
        if message.reply_to is not None:
            body["link"] = {"type": "reply", "mid": message.reply_to}
        payload = await self._post_message(int(message.address.chat_id), body)
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
            raise MaxRejectedError(
                f"MAX answered HTTP {response.status_code}",
                code=_error_code(response),
            )
        return _json_body(response)

    async def _post_message(self, chat_id: int, body: dict[str, Any]) -> dict[str, Any]:
        """Send one message, retrying only the documented attachment-processing delay."""
        for pause in (0.0, *ATTACHMENT_RETRY_SECONDS):
            if pause:
                await asyncio.sleep(pause)
            await self._pace(chat_id)
            try:
                return await self._request(
                    "POST",
                    "/messages",
                    params={"chat_id": chat_id},
                    json=body,
                )
            except MaxRejectedError as error:
                if error.code != ATTACHMENT_NOT_READY:
                    raise
        raise MaxError("MAX did not finish processing the image attachment")

    async def _image_token(self, name: str) -> str:
        async with self._image_lock:
            cached = self._image_tokens.get(name)
            if cached is not None:
                return cached
            path = asset_path(self._assets_dir, name)
            token = await self._upload_image(path)
            self._image_tokens[name] = token
            return token

    async def _upload_image(self, path: Path) -> str:
        reserved = await self._request("POST", "/uploads", params={"type": "image"})
        url = reserved.get("url")
        if not isinstance(url, str) or not url:
            raise MaxError("MAX upload response has no url")
        try:
            response = await self._client.post(
                url,
                files={"data": (path.name, path.read_bytes(), content_type(path))},
                headers={"Authorization": self._token.get_secret_value()},
            )
        except (httpx.TimeoutException, httpx.TransportError) as error:
            raise MaxUnavailableError(f"{type(error).__name__}: {error}") from None
        if response.status_code >= 500:
            raise MaxUnavailableError(f"MAX upload answered HTTP {response.status_code}")
        if response.status_code >= 400:
            raise MaxRejectedError(f"MAX upload answered HTTP {response.status_code}")
        token = upload_token(_json_body(response)) or upload_token(reserved)
        if token is None:
            raise MaxError("MAX upload response has no media token")
        return token

    async def _pace(self, chat_id: int) -> None:
        async with self._lock:
            last = self._last_sent.get(chat_id, 0.0)
            wait = self._min_interval - (time.monotonic() - last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_sent[chat_id] = time.monotonic()


def _json_body(response: httpx.Response) -> dict[str, Any]:
    if not response.content:
        return {}
    try:
        body = response.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def _error_code(response: httpx.Response) -> str | None:
    code = _json_body(response).get("code")
    return code if isinstance(code, str) and code else None


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
