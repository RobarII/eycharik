"""The webhook for every messenger: verify, deduplicate, persist a job, answer 200.

The route knows nothing about a messenger's payload. It looks the ``Ingress`` up by channel name
and does the same six things for everybody, which is why a second channel adds no branch here
(ADR 0019).

The webhook does no business work. Messengers retry a slow or failed delivery, so the only correct
answer is a fast acknowledgement after the event is durably queued.
"""

from __future__ import annotations

import json
from typing import cast

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import PlainTextResponse

from onboarding.app.db.queue import JobQueue
from onboarding.app.db.repos import SqlEventDeduper
from onboarding.core.models import Channel
from onboarding.ports import Ingress

router = APIRouter()

MAX_BODY_BYTES = 1_000_000
# VK wants this word; MAX and Telegram do not mind it, and one acknowledgement is one code path.
ACK = "ok"


def _ingress(request: Request, name: str) -> Ingress:
    container = request.app.state.container
    try:
        channel = Channel(name)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown channel") from None
    ingress = container.ingress.get(channel)
    if ingress is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown channel")
    return cast(Ingress, ingress)


async def _body(request: Request) -> bytes:
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "body too large")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_BODY_BYTES:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "body too large")
    return bytes(body)


@router.post("/webhook/{channel}", include_in_schema=False)
async def receive(channel: str, request: Request) -> PlainTextResponse:
    container = request.app.state.container
    ingress = _ingress(request, channel)
    if not ingress.configured:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "webhook secret is not configured"
        )
    body = await _body(request)
    headers = {name.lower(): value for name, value in request.headers.items()}
    if not ingress.verify(headers, body):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad webhook secret")

    # Every supported messenger posts JSON. A body that is not JSON is a misconfiguration, and
    # saying so is cheaper than an adapter guessing.
    try:
        json.loads(body)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid json") from None

    confirmation = ingress.handshake(body)
    if confirmation is not None:
        return PlainTextResponse(confirmation)

    inbound = ingress.parse(body, received_at=container.clock.now())
    if inbound is None:
        return PlainTextResponse(ACK)

    employee_id = await container.directory.resolve(inbound.address.channel, inbound.sender)
    if employee_id is None:
        # Access is a company fact, not a chat fact: an unlinked account gets no run (ADR 0019).
        await container.audit.record(
            "unlinked_channel_user",
            channel=inbound.address.channel.value,
            chat_id=int(inbound.address.chat_id),
            external_id=inbound.sender,
        )
        return PlainTextResponse(ACK)

    kind = "start" if inbound.starts_run else "message"
    job: dict[str, object] = {
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

    async with container.database.session() as session:
        if not await SqlEventDeduper(session).first_sighting(inbound.dedupe_key):
            return PlainTextResponse(ACK)
        await JobQueue.enqueue(session, kind, job)
    return PlainTextResponse(ACK)
