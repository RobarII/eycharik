"""HTTP client for the Telegram Bot API.

Facts and sources: ``docs/contracts/telegram-api.md``. The token is part of the URL, so it is
``SecretStr`` and never formatted into a log line: ``_url`` is the only place that reads it.
"""

from __future__ import annotations

import httpx
from pydantic import SecretStr

from onboarding.app.channels.markup import escape, to_reply_markup
from onboarding.app.channels.pacing import Pacer
from onboarding.core.channels import ChannelProfile
from onboarding.core.models import Address, Channel, Keyboard
from onboarding.ports import (
    ChannelRejectedError,
    ChannelUnavailableError,
    Messaging,
    OutboundMessage,
)


class TelegramError(RuntimeError):
    """Base class for Telegram API failures."""


class TelegramUnavailableError(ChannelUnavailableError):
    """Transport failure, a 5xx, or a 429: worth retrying later."""


class TelegramRejectedError(ChannelRejectedError):
    """4xx: the request is wrong and a retry will not help."""


class TelegramClient(Messaging):
    channel = Channel.TELEGRAM

    def __init__(
        self,
        *,
        base_url: str,
        token: SecretStr,
        client: httpx.AsyncClient,
        profile: ChannelProfile,
        timeout_s: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._client = client
        self._profile = profile
        self._timeout_s = timeout_s
        self._pacer = Pacer(
            per_second=profile.messages_per_second,
            per_chat_per_second=profile.per_chat_per_second,
        )

    async def send(self, message: OutboundMessage) -> str:
        body: dict[str, object] = {
            "chat_id": int(message.address.chat_id),
            "text": escape(message.text, self._profile.markup),
        }
        if self._profile.markup != "none":
            body["parse_mode"] = _PARSE_MODE[self._profile.markup]
        markup = to_reply_markup(message.keyboard)
        if markup is not None:
            body["reply_markup"] = markup
        if message.reply_to is not None:
            body["reply_to_message_id"] = message.reply_to
        payload = await self._call("sendMessage", body, chat_id=int(message.address.chat_id))
        message_id = _dig(payload, "result", "message_id")
        if not isinstance(message_id, int):
            raise TelegramError("Telegram response has no result.message_id")
        return str(message_id)

    async def edit(
        self, address: Address, message_id: str, text: str, keyboard: Keyboard = ()
    ) -> None:
        body: dict[str, object] = {
            "chat_id": int(address.chat_id),
            "message_id": int(message_id),
            "text": escape(text, self._profile.markup),
        }
        if self._profile.markup != "none":
            body["parse_mode"] = _PARSE_MODE[self._profile.markup]
        markup = to_reply_markup(keyboard)
        if markup is not None:
            body["reply_markup"] = markup
        await self._call("editMessageText", body, chat_id=int(address.chat_id))

    async def set_webhook(self, url: str, secret: SecretStr) -> None:
        await self._call(
            "setWebhook",
            {"url": url, "secret_token": secret.get_secret_value()},
            chat_id=0,
        )

    async def _call(
        self, method: str, body: dict[str, object], *, chat_id: int
    ) -> dict[str, object]:
        await self._pacer.wait(chat_id)
        try:
            response = await self._client.post(
                self._url(method), json=body, timeout=self._timeout_s
            )
        except (httpx.TimeoutException, httpx.TransportError) as error:
            raise TelegramUnavailableError(f"{type(error).__name__}: {error}") from None
        if response.status_code == 429 or response.status_code >= 500:
            raise TelegramUnavailableError(f"Telegram answered HTTP {response.status_code}")
        if response.status_code >= 400:
            raise TelegramRejectedError(
                f"Telegram answered HTTP {response.status_code}: {_description(response)}"
            )
        return _json_body(response)

    def _url(self, method: str) -> str:
        return f"{self._base_url}/bot{self._token.get_secret_value()}/{method}"


_PARSE_MODE = {"markdown": "Markdown", "markdownv2": "MarkdownV2", "html": "HTML", "none": ""}


def _json_body(response: httpx.Response) -> dict[str, object]:
    if not response.content:
        return {}
    try:
        body = response.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def _description(response: httpx.Response) -> str:
    description = _json_body(response).get("description")
    return description if isinstance(description, str) else "no description"


def _dig(payload: dict[str, object], *path: str) -> object:
    current: object = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current
