"""The webhook for every messenger: verify, deduplicate, persist a job, answer 200.

The route owns the body limit and the response format. Everything else — channel lookup, secret,
handshake, parse, identity gate, dedupe, enqueue — is one use case, so a second channel still adds
no branch here (ADR 0019).

The webhook does no business work. Messengers retry a slow or failed delivery, so the only correct
answer is a fast acknowledgement after the event is durably queued.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import PlainTextResponse

router = APIRouter()

MAX_BODY_BYTES = 1_000_000


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
    body = await _body(request)
    result = await request.app.state.container.inbound.execute(
        channel, request.headers, body
    )
    return PlainTextResponse(result.body)
