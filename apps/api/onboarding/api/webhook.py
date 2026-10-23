"""MAX webhook: verify, deduplicate, persist a job, answer 200.

The webhook does no business work. MAX retries a slow or failed delivery, so the only correct
answer is a fast acknowledgement after the event is durably queued.
"""

from __future__ import annotations

import hmac
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response, status

from onboarding.app.db.queue import JobQueue
from onboarding.app.db.repos import SqlEventDeduper
from onboarding.app.max.updates import parse_update
from onboarding.core.models import EmployeeId

router = APIRouter()

MAX_BODY_BYTES = 1_000_000


@router.post("/webhook", include_in_schema=False)
async def receive(request: Request) -> Response:
    container = request.app.state.container
    expected = container.settings.max_webhook_secret.get_secret_value()
    if not expected:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "webhook secret is not configured"
        )
    presented = request.headers.get("X-Max-Bot-Api-Secret", "")
    if not hmac.compare_digest(presented, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad webhook secret")

    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "body too large")

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_BODY_BYTES:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "body too large")
    try:
        payload: Any = json.loads(body)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid json") from None
    if not isinstance(payload, dict):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "expected an object")

    inbound = parse_update(payload, received_at=container.clock.now())
    if inbound is None:
        return Response(status_code=status.HTTP_200_OK)
    if inbound.user_id is None:
        await container.audit.record("webhook_without_sender", update=inbound.update_type)
        return Response(status_code=status.HTTP_200_OK)

    employee_id = EmployeeId(str(inbound.user_id))
    kind = "start" if inbound.update_type == "bot_started" else "message"
    job = {
        "employee_id": str(employee_id),
        "chat_id": int(inbound.chat_id),
        "event": {
            "kind": inbound.event.kind.value,
            "at": inbound.event.at.isoformat(),
            "text": inbound.event.text,
            "button_id": inbound.event.button_id,
        },
    }

    async with container.database.session() as session:
        if not await SqlEventDeduper(session).first_sighting(inbound.event_id):
            return Response(status_code=status.HTTP_200_OK)
        await JobQueue.enqueue(session, kind, job)
    return Response(status_code=status.HTTP_200_OK)
