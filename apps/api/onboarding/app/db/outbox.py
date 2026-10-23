"""Transactional outbox for outgoing messages.

Sending inside the state transaction would hold row locks across a network call. Instead the
message is written first and a dispatcher delivers it, retrying with backoff. Delivery is at least
once; a provider message id makes a repeat visible in the audit trail.

The row stores the *domain* message (channel, chat, text, keyboard of ``Button(id, text)``), never
a wire payload, so the adapter renders it and a renderer fix applies to already-queued rows
(ADR 0019).
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select, update

from onboarding.app.db.models import MessageRow
from onboarding.app.db.session import Database
from onboarding.core.channels import ChannelProfile, fit_text
from onboarding.core.models import Address, Button, Channel, ChatId, Keyboard
from onboarding.ports import (
    ChannelRejectedError,
    ChannelUnavailableError,
    Messaging,
    OutboundMessage,
)

MAX_ATTEMPTS = 5
BACKOFF_SECONDS = 5
# A claimed row keeps its lease for this long. A worker that dies after the claim but before the
# send leaves ``status='sending'``; when the lease expires the row returns to ``pending`` and is
# retried. Delivery is already at least once, so a lease that expires during a slow request costs
# a duplicate, never a lost message.
LEASE_SECONDS = 120


@dataclass(frozen=True, slots=True)
class PendingMessage:
    id: int
    address: Address
    text: str
    image: str | None
    keyboard: tuple[tuple[tuple[str, str], ...], ...]
    attempts: int


class OutboxMessaging:
    """Persist a message and let the dispatcher talk to the messenger of its address."""

    def __init__(
        self,
        database: Database,
        senders: Mapping[Channel, Messaging],
        profiles: Mapping[Channel, ChannelProfile],
    ) -> None:
        self._database = database
        self._senders = senders
        self._profiles = profiles

    async def send(self, message: OutboundMessage) -> str:
        """Write one row per part that fits the channel. Returns the id of the last part."""
        parts = fit_text(message.text, self._profiles[message.address.channel])
        async with self._database.session() as session:
            row_id = 0
            for index, part in enumerate(parts):
                row = MessageRow(
                    channel=message.address.channel.value,
                    chat_id=int(message.address.chat_id),
                    text=part,
                    # An image belongs to the message, not to a part: it rides on the first one.
                    image=message.image if index == 0 else None,
                    keyboard=_keyboard_json(message.keyboard),
                )
                session.add(row)
                await session.flush()
                row_id = row.id
            return str(row_id)

    async def edit(
        self, address: Address, message_id: str, text: str, keyboard: Keyboard = ()
    ) -> None:
        await self._senders[address.channel].edit(address, message_id, text, keyboard)


class MessageDispatcher:
    def __init__(
        self,
        database: Database,
        senders: Mapping[Channel, Messaging],
        *,
        batch: int = 20,
    ) -> None:
        self._database = database
        self._senders = senders
        self._batch = batch

    async def run_once(self) -> int:
        await self._reclaim_expired_leases()
        pending = await self._claim()
        # One slow channel must not hold back a fast one: each channel drains its own rows.
        by_channel: dict[Channel, list[PendingMessage]] = {}
        for message in pending:
            by_channel.setdefault(message.address.channel, []).append(message)
        await asyncio.gather(
            *(self._deliver_all(channel, rows) for channel, rows in by_channel.items())
        )
        return len(pending)

    async def _deliver_all(self, channel: Channel, rows: list[PendingMessage]) -> None:
        for message in rows:
            await self._deliver(channel, message)

    async def _reclaim_expired_leases(self) -> None:
        """Return rows abandoned mid-send to the queue; the lease is in ``available_at``."""
        async with self._database.session() as session:
            await session.execute(
                update(MessageRow)
                .where(
                    MessageRow.status == "sending",
                    MessageRow.available_at <= func.now(),
                )
                .values(status="pending")
            )

    async def _claim(self) -> tuple[PendingMessage, ...]:
        claimable = (
            select(MessageRow.id)
            .where(MessageRow.status == "pending", MessageRow.available_at <= func.now())
            .order_by(MessageRow.id)
            .limit(self._batch)
            .with_for_update(skip_locked=True)
        )
        async with self._database.session() as session:
            rows = await session.scalars(
                update(MessageRow)
                .where(MessageRow.id.in_(claimable))
                .values(
                    status="sending",
                    available_at=func.now() + timedelta(seconds=LEASE_SECONDS),
                )
                .returning(MessageRow)
            )
            return tuple(
                PendingMessage(
                    id=row.id,
                    address=Address(channel=Channel(row.channel), chat_id=ChatId(row.chat_id)),
                    text=row.text,
                    image=row.image,
                    keyboard=tuple(
                        tuple((button["id"], button["text"]) for button in line)
                        for line in row.keyboard
                    ),
                    attempts=row.attempts,
                )
                for row in rows
            )

    async def _deliver(self, channel: Channel, message: PendingMessage) -> None:
        keyboard: Keyboard = tuple(
            tuple(Button(id=button_id, text=text) for button_id, text in line)
            for line in message.keyboard
        )
        sender = self._senders.get(channel)
        if sender is None:
            await self._park(message, f"channel {channel} is not configured")
            return
        try:
            external_id = await sender.send(
                OutboundMessage(
                    address=message.address,
                    text=message.text,
                    image=message.image,
                    keyboard=keyboard,
                )
            )
        except ChannelRejectedError as error:
            await self._park(message, str(error))
            return
        except ChannelUnavailableError as error:
            await self._retry(message, error)
            return
        except Exception as error:  # noqa: BLE001 - a bug in one adapter must not stop the outbox
            await self._retry(message, error)
            return
        async with self._database.session() as session:
            await session.execute(
                update(MessageRow)
                .where(MessageRow.id == message.id)
                .values(status="sent", external_id=external_id, sent_at=func.now())
            )

    async def _retry(self, message: PendingMessage, error: Exception) -> None:
        attempts = message.attempts + 1
        async with self._database.session() as session:
            await session.execute(
                update(MessageRow)
                .where(MessageRow.id == message.id)
                .values(
                    status="pending" if attempts < MAX_ATTEMPTS else "failed",
                    attempts=attempts,
                    available_at=func.now() + timedelta(seconds=BACKOFF_SECONDS * attempts),
                    last_error=str(error)[:500],
                )
            )

    async def _park(self, message: PendingMessage, reason: str) -> None:
        """A refusal will be refused again; keep the row visible instead of retrying it."""
        async with self._database.session() as session:
            await session.execute(
                update(MessageRow)
                .where(MessageRow.id == message.id)
                .values(status="failed", attempts=message.attempts + 1, last_error=reason[:500])
            )


def _keyboard_json(keyboard: Keyboard) -> list[list[dict[str, str]]]:
    return [[{"id": button.id, "text": button.text} for button in line] for line in keyboard]
