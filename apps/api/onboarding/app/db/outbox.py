"""Transactional outbox for outgoing messages.

Sending inside the state transaction would hold row locks across a network call. Instead the
message is written first and a dispatcher delivers it, retrying with backoff. Delivery is at least
once; MAX message ids make a repeat visible in the audit trail.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select, update

from onboarding.app.db.models import MessageRow
from onboarding.app.db.session import Database
from onboarding.core.models import Button, ChatId, Keyboard
from onboarding.ports import Messaging, OutboundMessage

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
    chat_id: ChatId
    text: str
    image: str | None
    keyboard: tuple[tuple[tuple[str, str], ...], ...]
    attempts: int


class OutboxMessaging:
    """Persist a message and let the dispatcher talk to MAX."""

    def __init__(self, database: Database, direct: Messaging) -> None:
        self._database = database
        self._direct = direct

    async def send(self, message: OutboundMessage) -> str:
        async with self._database.session() as session:
            row = MessageRow(
                chat_id=int(message.chat_id),
                text=message.text,
                image=message.image,
                keyboard=_keyboard_json(message.keyboard),
            )
            session.add(row)
            await session.flush()
            return str(row.id)

    async def edit(self, message_id: str, text: str, keyboard: Keyboard = ()) -> None:
        await self._direct.edit(message_id, text, keyboard)


class MessageDispatcher:
    def __init__(self, database: Database, sender: Messaging, *, batch: int = 20) -> None:
        self._database = database
        self._sender = sender
        self._batch = batch

    async def run_once(self) -> int:
        await self._reclaim_expired_leases()
        pending = await self._claim()
        for message in pending:
            await self._deliver(message)
        return len(pending)

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
                    chat_id=ChatId(row.chat_id),
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

    async def _deliver(self, message: PendingMessage) -> None:
        keyboard: Keyboard = tuple(
            tuple(Button(id=button_id, text=text) for button_id, text in line)
            for line in message.keyboard
        )
        try:
            external_id = await self._sender.send(
                OutboundMessage(
                    chat_id=message.chat_id,
                    text=message.text,
                    image=message.image,
                    keyboard=keyboard,
                )
            )
        except Exception as error:  # noqa: BLE001 - the dispatcher must not crash on one message
            await self._mark_failed(message, error)
            return
        async with self._database.session() as session:
            await session.execute(
                update(MessageRow)
                .where(MessageRow.id == message.id)
                .values(status="sent", external_id=external_id, sent_at=func.now())
            )

    async def _mark_failed(self, message: PendingMessage, error: Exception) -> None:
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


def _keyboard_json(keyboard: Keyboard) -> list[list[dict[str, str]]]:
    return [[{"id": button.id, "text": button.text} for button in line] for line in keyboard]
