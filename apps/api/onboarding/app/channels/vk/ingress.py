"""VK Callback API payloads to typed inbound messages.

Facts and sources: ``docs/contracts/vk-api.md``. VK differs from the other two in two ways the port
absorbs: its secret travels in the payload rather than a header, and it asks for a confirmation
handshake before it delivers anything.
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

START_COMMAND = "/start"
CONFIRMATION = "confirmation"


class VkIngress:
    """VK inbound: payload secret, confirmation handshake, one event shape."""

    channel = Channel.VK

    def __init__(self, secret: SecretStr, confirmation: SecretStr) -> None:
        self._secret = secret
        self._confirmation = confirmation

    @property
    def configured(self) -> bool:
        return bool(self._secret.get_secret_value()) and bool(
            self._confirmation.get_secret_value()
        )

    def verify(self, headers: Mapping[str, str], body: bytes) -> bool:
        del headers
        expected = self._secret.get_secret_value()
        if not expected:
            return False
        presented = _json(body).get("secret")
        return isinstance(presented, str) and hmac.compare_digest(presented, expected)

    def handshake(self, body: bytes) -> str | None:
        if _json(body).get("type") != CONFIRMATION:
            return None
        return self._confirmation.get_secret_value()

    def parse(self, body: bytes, *, received_at: datetime) -> InboundMessage | None:
        payload = _json(body)
        event_id = payload.get("event_id")
        if isinstance(event_id, bool) or not isinstance(event_id, str) or not event_id:
            return None
        kind = payload.get("type")
        if kind == "message_new":
            return _message(event_id, _mapping(payload.get("object")), received_at)
        if kind == "message_event":
            return _button(event_id, _mapping(payload.get("object")), received_at)
        return None


def _message(
    event_id: str, container: Mapping[str, Any], received_at: datetime
) -> InboundMessage | None:
    message = _mapping(container.get("message"))
    peer_id = message.get("peer_id")
    sender = message.get("from_id")
    if not isinstance(peer_id, int) or not isinstance(sender, int):
        return None
    at = _at(message, received_at)
    text = message.get("text")
    clean = text.strip() if isinstance(text, str) and text.strip() else None
    if clean is not None and clean.startswith(START_COMMAND):
        event = Event(kind=EventKind.EMPLOYEE_CREATED, at=at)
        return _inbound(event_id, peer_id, sender, event, starts_run=True)
    attachment = _attachment_id(message)
    if attachment is not None:
        event = Event(kind=EventKind.FILE_RECEIVED, at=at, file_id=attachment)
        return _inbound(event_id, peer_id, sender, event, starts_run=False)
    return _inbound(
        event_id,
        peer_id,
        sender,
        Event(kind=EventKind.MESSAGE_RECEIVED, at=at, text=clean),
        starts_run=False,
    )


def _button(
    event_id: str, payload: Mapping[str, Any], received_at: datetime
) -> InboundMessage | None:
    peer_id = payload.get("peer_id")
    sender = payload.get("user_id")
    if not isinstance(peer_id, int) or not isinstance(sender, int):
        return None
    raw = payload.get("event_id")
    event = Event(
        kind=EventKind.BUTTON_PRESSED,
        at=_at(payload, received_at),
        button_id=_button_id(payload.get("payload") or raw),
    )
    return _inbound(event_id, peer_id, sender, event, starts_run=False)


def _inbound(
    event_id: str,
    peer_id: int,
    sender: int,
    event: Event,
    *,
    starts_run: bool,
) -> InboundMessage:
    return InboundMessage(
        dedupe_key=f"{Channel.VK.value}:{event_id}",
        address=Address(channel=Channel.VK, chat_id=ChatId(peer_id)),
        sender=str(sender),
        event=event,
        starts_run=starts_run,
    )


def _button_id(raw: object) -> str | None:
    """A callback button carries ``{"id": ...}``; older payloads carry the id itself."""
    if isinstance(raw, str):
        try:
            decoded: Any = json.loads(raw)
        except ValueError:
            return raw or None
        if isinstance(decoded, Mapping):
            value = decoded.get("id")
            return value if isinstance(value, str) and value else None
        return raw or None
    if isinstance(raw, Mapping):
        value = raw.get("id")
        return value if isinstance(value, str) and value else None
    return None


def _attachment_id(message: Mapping[str, Any]) -> str | None:
    attachments = message.get("attachments")
    if not isinstance(attachments, list):
        return None
    for attachment in attachments:
        if not isinstance(attachment, Mapping):
            continue
        kind = attachment.get("type")
        body = attachment.get(kind) if isinstance(kind, str) else None
        identifier = _digest(body) if not isinstance(body, Mapping) else _identity(body)
        if identifier is not None:
            return identifier
    return None


def _identity(body: Mapping[str, Any]) -> str | None:
    for key in ("access_key", "id", "owner_id"):
        value = body.get(key)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, int) and not isinstance(value, bool):
            return str(value)
    return _digest(body)


def _json(body: bytes) -> Mapping[str, Any]:
    try:
        payload: Any = json.loads(body)
    except ValueError:
        return {}
    return payload if isinstance(payload, Mapping) else {}


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _at(message: Mapping[str, Any], received_at: datetime) -> datetime:
    value = message.get("date")
    if isinstance(value, bool) or not isinstance(value, int | float):
        return received_at
    return datetime.fromtimestamp(value, tz=UTC)


def _digest(payload: object) -> str:
    material = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
