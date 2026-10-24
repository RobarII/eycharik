"""MAX webhook payloads to typed inbound messages.

Parsing is defensive: an unknown update type is ignored, a missing field degrades to ``None``
rather than an exception, and an unknown callback payload still produces a button event. MAX can
add fields without breaking delivery.

The payload shapes are pinned in ``docs/contracts/max-api.md``; tests use synthetic payloads until
a captured one exists. The port this implements is ``docs/contracts/channel.md``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import SecretStr

from onboarding.core.models import Address, Channel, ChatId, Event, EventKind
from onboarding.ports import InboundMessage

HANDLED_TYPES = frozenset({"message_created", "message_callback", "bot_started"})
SECRET_HEADER = "X-Max-Bot-Api-Secret"  # noqa: S105 - a header name, not a secret


class MaxIngress:
    """MAX inbound: one shared secret header, one payload shape."""

    channel = Channel.MAX

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
        presented = headers.get(SECRET_HEADER, "") or headers.get(SECRET_HEADER.lower(), "")
        return hmac.compare_digest(presented, expected)

    def handshake(self, body: bytes) -> str | None:
        del body
        return None

    def parse(self, body: bytes, *, received_at: datetime) -> InboundMessage | None:
        try:
            payload: Any = json.loads(body)
        except ValueError:
            return None
        if not isinstance(payload, dict):
            return None
        update = parse_update(payload, received_at=received_at)
        if update is None or update.user_id is None:
            return None
        return InboundMessage(
            dedupe_key=f"{self.channel.value}:{update.event_id}",
            address=Address(channel=self.channel, chat_id=update.chat_id),
            sender=str(update.user_id),
            event=update.event,
            starts_run=update.update_type == "bot_started",
        )


@dataclass(frozen=True, slots=True)
class InboundUpdate:
    event_id: str
    update_type: str
    chat_id: ChatId
    user_id: int | None
    event: Event


def parse_update(payload: Mapping[str, Any], *, received_at: datetime) -> InboundUpdate | None:
    """Return a typed update, or ``None`` when the type is not ours to handle."""
    update_type = payload.get("update_type")
    if not isinstance(update_type, str) or update_type not in HANDLED_TYPES:
        return None

    message = _mapping(payload.get("message"))
    body = _mapping(message.get("body"))
    sender = _mapping(message.get("sender"))
    recipient = _mapping(message.get("recipient"))
    callback = _mapping(payload.get("callback"))
    chat_id = _int(payload.get("chat_id")) or _int(recipient.get("chat_id"))
    if chat_id is None:
        return None

    at = _timestamp(payload.get("timestamp")) or received_at
    # A callback carries the presser in ``callback.user``; the outer ``user`` is absent and
    # ``message.sender`` is the bot that owns the keyboard, so neither may be used for it.
    user_id = _int(_mapping(payload.get("user")).get("user_id"))
    if user_id is None:
        user_id = _int(_mapping(callback.get("user")).get("user_id"))
    if user_id is None and update_type != "message_callback":
        user_id = _int(sender.get("user_id"))

    mid = body.get("mid")
    press_id = callback.get("callback_id")
    event_id = (
        str(press_id)
        if update_type == "message_callback" and isinstance(press_id, str) and press_id
        else str(mid)
        if isinstance(mid, str) and mid
        else _synthetic_id(update_type, payload, chat_id)
    )

    if update_type == "bot_started":
        event = Event(kind=EventKind.EMPLOYEE_CREATED, at=at)
    elif update_type == "message_created":
        text = body.get("text")
        event = Event(
            kind=EventKind.MESSAGE_RECEIVED,
            at=at,
            text=text.strip() if isinstance(text, str) and text.strip() else None,
        )
    else:
        button_id = _callback_id(payload)
        event = Event(kind=EventKind.BUTTON_PRESSED, at=at, button_id=button_id)

    return InboundUpdate(
        event_id=event_id,
        update_type=update_type,
        chat_id=ChatId(chat_id),
        user_id=user_id,
        event=event,
    )


def _callback_id(payload: Mapping[str, Any]) -> str | None:
    callback = payload.get("callback")
    if isinstance(callback, Mapping):
        for key in ("payload", "button_id", "data"):
            value = callback.get(key)
            if isinstance(value, str) and value:
                return value
    for key in ("payload", "button_id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _synthetic_id(update_type: str, payload: Mapping[str, Any], chat_id: int) -> str:
    material = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
    return f"{update_type}:{chat_id}:{digest}"


def _timestamp(value: object) -> datetime | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def _int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
