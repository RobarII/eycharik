"""Telegram updates to typed inbound messages.

Facts and sources: ``docs/contracts/telegram-api.md``. Parsing is defensive in the same way the MAX
one is: an unknown update returns ``None``, a missing field degrades, and no delivery raises.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from pydantic import SecretStr

from onboarding.core.models import Address, Channel, ChatId, Event, EventKind
from onboarding.ports import InboundMessage

SECRET_HEADER = "x-telegram-bot-api-secret-token"  # noqa: S105 - a header name, not a secret
START_COMMAND = "/start"


class TelegramIngress:
    """Telegram inbound: the secret-token header, and one update shape."""

    channel = Channel.TELEGRAM

    def __init__(self, secret: SecretStr) -> None:
        self._secret = secret

    @property
    def configured(self) -> bool:
        return bool(self._secret.get_secret_value())

    def verify(self, headers: Mapping[str, str], body: bytes) -> bool:
        del body
        expected = self._secret.get_secret_value()
        if not expected:
            return False
        return _compare(headers.get(SECRET_HEADER, ""), expected)

    def handshake(self, body: bytes) -> str | None:
        del body
        return None

    def parse(self, body: bytes, *, received_at: datetime) -> InboundMessage | None:
        payload = _json(body)
        if payload is None:
            return None
        update_id = payload.get("update_id")
        if isinstance(update_id, bool) or not isinstance(update_id, int):
            return None
        callback = _mapping(payload.get("callback_query"))
        if callback:
            return _callback(update_id, callback, received_at)
        message = _mapping(payload.get("message"))
        if not message:
            return None
        return _message(update_id, message, received_at)


def _callback(
    update_id: int, callback: Mapping[str, Any], received_at: datetime
) -> InboundMessage | None:
    message = _mapping(callback.get("message"))
    chat_id = _chat_id(message)
    sender = _user_id(_mapping(callback.get("from")))
    if chat_id is None or sender is None:
        return None
    data = callback.get("data")
    event = Event(
        kind=EventKind.BUTTON_PRESSED,
        at=_at(message, received_at),
        button_id=data if isinstance(data, str) and data else None,
    )
    return _inbound(update_id, chat_id, sender, event, starts_run=False)


def _message(
    update_id: int, message: Mapping[str, Any], received_at: datetime
) -> InboundMessage | None:
    chat_id = _chat_id(message)
    sender = _user_id(_mapping(message.get("from")))
    if chat_id is None or sender is None:
        return None
    at = _at(message, received_at)
    text = message.get("text")
    clean = text.strip() if isinstance(text, str) and text.strip() else None
    if clean is not None and clean.startswith(START_COMMAND):
        event = Event(kind=EventKind.EMPLOYEE_CREATED, at=at)
        return _inbound(update_id, chat_id, sender, event, starts_run=True)
    if message.get("document"):
        event = Event(kind=EventKind.FILE_RECEIVED, at=at, file_id=_document_id(message))
        return _inbound(update_id, chat_id, sender, event, starts_run=False)
    event = Event(kind=EventKind.MESSAGE_RECEIVED, at=at, text=clean)
    return _inbound(update_id, chat_id, sender, event, starts_run=False)


def _inbound(
    update_id: int,
    chat_id: int,
    sender: str,
    event: Event,
    *,
    starts_run: bool,
) -> InboundMessage:
    return InboundMessage(
        dedupe_key=f"{Channel.TELEGRAM.value}:{update_id}",
        address=Address(channel=Channel.TELEGRAM, chat_id=ChatId(chat_id)),
        sender=sender,
        event=event,
        starts_run=starts_run,
    )


def _json(body: bytes) -> Mapping[str, Any] | None:
    try:
        payload: Any = json.loads(body)
    except ValueError:
        return None
    return payload if isinstance(payload, Mapping) else None


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _chat_id(message: Mapping[str, Any]) -> int | None:
    chat = _mapping(message.get("chat"))
    value = chat.get("id")
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _user_id(user: Mapping[str, Any]) -> str | None:
    value = user.get("id")
    return str(value) if isinstance(value, int) and not isinstance(value, bool) else None


def _document_id(message: Mapping[str, Any]) -> str | None:
    document = _mapping(message.get("document"))
    value = document.get("file_unique_id") or document.get("file_id")
    return value if isinstance(value, str) and value else _digest(message)


def _at(message: Mapping[str, Any], received_at: datetime) -> datetime:
    value = message.get("date")
    if isinstance(value, bool) or not isinstance(value, int | float):
        return received_at
    return datetime.fromtimestamp(value, tz=UTC)


def _digest(payload: object) -> str:
    material = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def _compare(presented: str, expected: str) -> bool:
    return hmac.compare_digest(presented, expected)
