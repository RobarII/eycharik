from __future__ import annotations

import json

import httpx
import pytest
from pydantic import SecretStr

from onboarding.app.channels.max.client import (
    MaxClient,
    MaxRejectedError,
    MaxUnavailableError,
    Subscription,
)
from onboarding.app.channels.max.render import to_attachments
from onboarding.core.models import Address, Button, Channel, ChatId
from onboarding.ports import OutboundMessage

ADDRESS = Address(channel=Channel.MAX, chat_id=ChatId(1))


def build(
    handler: httpx.MockTransport, messages_per_second: float = 1000.0
) -> MaxClient:
    return MaxClient(
        base_url="https://max.test",
        token=SecretStr("bot-token"),
        client=httpx.AsyncClient(transport=handler),
        messages_per_second=messages_per_second,
    )


def test_keyboard_maps_to_an_inline_attachment() -> None:
    attachments = to_attachments(((Button(id="start", text="Начать"),),))

    assert attachments == [
        {
            "type": "inline_keyboard",
            "payload": {"buttons": [[{"type": "callback", "text": "Начать", "payload": "start"}]]},
        }
    ]


async def test_send_posts_text_and_keyboard() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"message": {"body": {"mid": "mid-42"}}})

    client = build(httpx.MockTransport(handler))
    message = OutboundMessage(
        address=Address(channel=Channel.MAX, chat_id=ChatId(111)),
        text="Привет",
        keyboard=((Button(id="go", text="Дальше"),),),
    )

    mid = await client.send(message)

    assert mid == "mid-42"
    request = calls[0]
    assert request.method == "POST"
    assert request.url.path == "/messages"
    assert request.url.params["chat_id"] == "111"
    assert request.headers["authorization"] == "bot-token"
    assert json.loads(request.content)["text"] == "Привет"


async def test_send_without_keyboard_has_no_attachments() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"message": {"body": {"mid": "m"}}})

    await build(httpx.MockTransport(handler)).send(OutboundMessage(address=ADDRESS, text="x"))

    assert "attachments" not in json.loads(seen[0].content)


async def test_edit_uses_put() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    await build(httpx.MockTransport(handler)).edit(ADDRESS, "mid-1", "Новый текст")

    assert seen[0].method == "PUT"
    assert seen[0].url.path == "/messages/mid-1"


async def test_client_error_is_rejected() -> None:
    handler = httpx.MockTransport(lambda request: httpx.Response(401, json={}))

    with pytest.raises(MaxRejectedError):
        await build(handler).send(OutboundMessage(address=ADDRESS, text="x"))


async def test_server_error_is_unavailable() -> None:
    handler = httpx.MockTransport(lambda request: httpx.Response(503, json={}))

    with pytest.raises(MaxUnavailableError):
        await build(handler).send(OutboundMessage(address=ADDRESS, text="x"))


async def test_subscription_posts_the_secret() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    await build(httpx.MockTransport(handler)).subscribe(
        Subscription(
            url="https://example.test/webhook/max",
            update_types=("message_created",),
            secret=SecretStr("s3cret"),
        )
    )

    body = json.loads(seen[0].content)
    assert body == {
        "url": "https://example.test/webhook/max",
        "update_types": ["message_created"],
        "secret": "s3cret",
    }
