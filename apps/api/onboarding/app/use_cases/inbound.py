"""Accept one messenger delivery without knowing HTTP or SQL.

The use case owns the sequence: channel lookup, secret check, handshake, parse, identity gate,
dedupe, enqueue. The route owns one thing: call it and translate the result to a status code.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass

from onboarding.app.jobs import MESSAGE, START
from onboarding.core.models import Channel
from onboarding.ports import AuditLog, Clock, Directory, InboundSink, Ingress

ACK = "ok"


class InboundError(Exception):
    """A delivery that cannot be accepted."""


class UnknownChannelError(InboundError):
    """No configured ingress answers to this path segment."""


class ChannelUnavailableError(InboundError):
    """The channel exists but its secret is not configured, so it cannot authenticate anyone."""


class BadSecretError(InboundError):
    """The delivery did not prove it came from the messenger."""


class InvalidBodyError(InboundError):
    """The messenger sent something that is not JSON."""


@dataclass(frozen=True, slots=True)
class InboundResult:
    body: str


class AcceptInbound:
    def __init__(
        self,
        *,
        ingress: Mapping[Channel, Ingress],
        directory: Directory,
        audit: AuditLog,
        clock: Clock,
        sink: InboundSink,
    ) -> None:
        self._ingress = ingress
        self._directory = directory
        self._audit = audit
        self._clock = clock
        self._sink = sink

    async def execute(
        self, channel_name: str, headers: Mapping[str, str], body: bytes
    ) -> InboundResult:
        try:
            channel = Channel(channel_name)
        except ValueError:
            raise UnknownChannelError(channel_name) from None
        ingress = self._ingress.get(channel)
        if ingress is None:
            raise UnknownChannelError(channel_name)
        if not ingress.configured:
            raise ChannelUnavailableError(channel_name)
        if not ingress.verify(_lower(headers), body):
            raise BadSecretError(channel_name)

        try:
            json.loads(body)
        except ValueError:
            raise InvalidBodyError(channel_name) from None

        confirmation = ingress.handshake(body)
        if confirmation is not None:
            return InboundResult(body=confirmation)

        inbound = ingress.parse(body, received_at=self._clock.now())
        if inbound is None:
            return InboundResult(body=ACK)

        employee_id = await self._directory.resolve(inbound.address.channel, inbound.sender)
        if employee_id is None:
            # Access is a company fact, not a chat fact: an unlinked account gets no run.
            await self._audit.record(
                "unlinked_channel_user",
                channel=inbound.address.channel.value,
                chat_id=int(inbound.address.chat_id),
                external_id=inbound.sender,
            )
            return InboundResult(body=ACK)

        kind = START if inbound.starts_run else MESSAGE
        payload: dict[str, object] = {
            "employee_id": str(employee_id),
            "channel": inbound.address.channel.value,
            "chat_id": int(inbound.address.chat_id),
            "event": {
                "kind": inbound.event.kind.value,
                "at": inbound.event.at.isoformat(),
                "text": inbound.event.text,
                "button_id": inbound.event.button_id,
                "file_id": inbound.event.file_id,
            },
        }
        await self._sink.accept(
            dedupe_key=inbound.dedupe_key,
            job_kind=kind,
            payload=payload,
        )
        return InboundResult(body=ACK)


def _lower(headers: Mapping[str, str]) -> dict[str, str]:
    return {name.lower(): value for name, value in headers.items()}
