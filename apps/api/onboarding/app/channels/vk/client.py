"""HTTP client for the VK Callback API's outbound half.

Facts and sources: ``docs/contracts/vk-api.md``. Two VK traits shape this class: it answers HTTP 200
with an ``error`` object instead of a status code, and its keyboard belongs to the dialog rather
than to a message, so a message without buttons must say so explicitly.
"""

from __future__ import annotations

import json
import secrets
from typing import Any

import httpx
from pydantic import SecretStr

from onboarding.app.channels.pacing import Pacer
from onboarding.core.channels import ChannelProfile
from onboarding.core.models import Address, Channel, Keyboard
from onboarding.ports import (
    ChannelRejectedError,
    ChannelUnavailableError,
    Messaging,
    OutboundMessage,
)

# VK documents these as "try again later" rather than "your request is wrong".
_RETRYABLE_CODES = frozenset({1, 6, 9, 10})
_EMPTY_KEYBOARD: dict[str, object] = {"buttons": []}


class VkError(RuntimeError):
    """Base class for VK API failures."""


class VkUnavailableError(ChannelUnavailableError):
    """Transport failure, a 5xx, or a documented "too many requests" code."""


class VkRejectedError(ChannelRejectedError):
    """A VK error code that a retry cannot fix."""


class VkClient(Messaging):
    channel = Channel.VK

    def __init__(
        self,
        *,
        base_url: str,
        api_version: str,
        token: SecretStr,
        client: httpx.AsyncClient,
        profile: ChannelProfile,
        timeout_s: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_version = api_version
        self._token = token
        self._client = client
        self._profile = profile
        self._timeout_s = timeout_s
        self._pacer = Pacer(
            per_second=profile.messages_per_second,
            per_chat_per_second=profile.per_chat_per_second,
        )

    async def send(self, message: OutboundMessage) -> str:
        peer_id = int(message.address.chat_id)
        params: dict[str, object] = {
            "peer_id": peer_id,
            "message": message.text,
            # VK drops a repeat with the same random_id, so this is also how a retry stays unique.
            "random_id": secrets.randbits(63),
            "keyboard": _keyboard(message.keyboard, self._profile),
        }
        if message.reply_to is not None:
            params["reply_to"] = message.reply_to
        response = await self._call("messages.send", params, peer_id=peer_id)
        return str(response) if isinstance(response, int) else str(peer_id)

    async def edit(
        self, address: Address, message_id: str, text: str, keyboard: Keyboard = ()
    ) -> None:
        peer_id = int(address.chat_id)
        await self._call(
            "messages.edit",
            {
                "peer_id": peer_id,
                "message_id": int(message_id),
                "message": text,
                "keyboard": _keyboard(keyboard, self._profile),
            },
            peer_id=peer_id,
        )

    async def _call(self, method: str, params: dict[str, object], *, peer_id: int) -> object:
        await self._pacer.wait(peer_id)
        body = {"access_token": self._token.get_secret_value(), "v": self._api_version}
        body.update(_wire(params))
        try:
            response = await self._client.post(
                f"{self._base_url}/method/{method}", data=body, timeout=self._timeout_s
            )
        except (httpx.TimeoutException, httpx.TransportError) as error:
            raise VkUnavailableError(f"{type(error).__name__}: {error}") from None
        if response.status_code >= 500:
            raise VkUnavailableError(f"VK answered HTTP {response.status_code}")
        if response.status_code == 429:
            raise VkUnavailableError("VK answered HTTP 429")
        if response.status_code >= 400:
            raise VkRejectedError(f"VK answered HTTP {response.status_code}")
        payload = _json(response)
        failure = payload.get("error")
        if isinstance(failure, dict):
            raise _failure(failure)
        return payload.get("response")


def _failure(payload: dict[str, Any]) -> Exception:
    code = payload.get("error_code")
    message = payload.get("error_msg")
    detail = f"VK error {code}: {message if isinstance(message, str) else 'no message'}"
    return VkUnavailableError(detail) if code in _RETRYABLE_CODES else VkRejectedError(detail)


def _keyboard(keyboard: Keyboard, profile: ChannelProfile) -> str:
    """VK keeps the previous keyboard unless the new message replaces it explicitly."""
    rows = [
        [
            {
                "action": {
                    "type": "callback",
                    "label": button.text,
                    "payload": json.dumps({"id": button.id}, ensure_ascii=False),
                }
            }
            for button in row
        ]
        for row in keyboard
    ]
    shape: dict[str, object] = {"one_time": False, "buttons": rows}
    if profile.keyboard_scope == "message":
        shape["inline"] = True
    return json.dumps(shape if rows else _EMPTY_KEYBOARD, ensure_ascii=False)


def _wire(params: dict[str, object]) -> dict[str, str]:
    return {key: value if isinstance(value, str) else str(value) for key, value in params.items()}


def _json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload: Any = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


__all__ = ["VkClient", "VkError", "VkRejectedError", "VkUnavailableError"]
