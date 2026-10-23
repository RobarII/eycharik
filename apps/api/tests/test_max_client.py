from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

import onboarding.app.max.client as client_module
from onboarding.app.max.client import (
    MaxClient,
    MaxRejectedError,
    MaxUnavailableError,
    Subscription,
)
from onboarding.app.max.keyboards import to_attachments
from onboarding.app.max.media import ImageAssetError
from onboarding.core.models import Button, ChatId
from onboarding.ports import OutboundMessage


def build(
    handler: httpx.MockTransport,
    messages_per_second: float = 1000.0,
    assets_dir: Path | None = None,
) -> MaxClient:
    return MaxClient(
        base_url="https://max.test",
        token=SecretStr("bot-token"),
        client=httpx.AsyncClient(transport=handler),
        messages_per_second=messages_per_second,
        assets_dir=assets_dir,
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
        chat_id=ChatId(111),
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

    await build(httpx.MockTransport(handler)).send(OutboundMessage(chat_id=ChatId(1), text="x"))

    assert "attachments" not in json.loads(seen[0].content)


async def test_send_uploads_an_image_once_and_reuses_the_token(tmp_path: Path) -> None:
    (tmp_path / "welcome.jpg").write_bytes(b"jpeg bytes")
    uploads: list[httpx.Request] = []
    messages: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "max.test" and request.url.path == "/uploads":
            assert request.url.params["type"] == "image"
            return httpx.Response(
                200, json={"url": "https://upload.test/image", "token": "reserved"}
            )
        if request.url.host == "upload.test":
            uploads.append(request)
            return httpx.Response(
                200, json={"photos": {"photoIds": {"token": "media-token"}}}
            )
        messages.append(request)
        return httpx.Response(200, json={"message": {"body": {"mid": "mid-1"}}})

    client = build(httpx.MockTransport(handler), assets_dir=tmp_path)
    message = OutboundMessage(
        chat_id=ChatId(7),
        text="Привет",
        image="welcome.jpg",
        keyboard=((Button(id="go", text="Дальше"),),),
    )

    assert await client.send(message) == "mid-1"
    assert await client.send(message) == "mid-1"

    assert len(uploads) == 1
    assert uploads[0].headers["content-type"].startswith("multipart/form-data")
    assert len(messages) == 2
    attachments = json.loads(messages[0].content)["attachments"]
    assert attachments[0] == {"type": "image", "payload": {"token": "media-token"}}
    assert attachments[1]["type"] == "inline_keyboard"


async def test_an_unprocessed_image_is_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "welcome.jpg").write_bytes(b"jpeg bytes")
    monkeypatch.setattr(client_module, "ATTACHMENT_RETRY_SECONDS", (0.0, 0.0))
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        if request.url.host == "upload.test":
            return httpx.Response(
                200, json={"photos": {"photoIds": {"token": "media-token"}}}
            )
        if request.url.path == "/uploads":
            return httpx.Response(200, json={"url": "https://upload.test/image"})
        attempts += 1
        if attempts == 1:
            return httpx.Response(400, json={"code": "attachment.not.ready"})
        return httpx.Response(200, json={"message": {"body": {"mid": "mid-1"}}})

    client = build(httpx.MockTransport(handler), assets_dir=tmp_path)

    mid = await client.send(OutboundMessage(chat_id=ChatId(1), text="x", image="welcome.jpg"))

    assert mid == "mid-1"
    assert attempts == 2


async def test_a_missing_image_fails_before_the_request(tmp_path: Path) -> None:
    client = build(
        httpx.MockTransport(lambda request: httpx.Response(200, json={})), assets_dir=tmp_path
    )

    with pytest.raises(ImageAssetError, match="missing"):
        await client.send(OutboundMessage(chat_id=ChatId(1), text="x", image="ghost.jpg"))


async def test_edit_uses_put() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    await build(httpx.MockTransport(handler)).edit("mid-1", "Новый текст")

    assert seen[0].method == "PUT"
    assert seen[0].url.path == "/messages/mid-1"


async def test_client_error_is_rejected() -> None:
    handler = httpx.MockTransport(lambda request: httpx.Response(401, json={}))

    with pytest.raises(MaxRejectedError):
        await build(handler).send(OutboundMessage(chat_id=ChatId(1), text="x"))


async def test_server_error_is_unavailable() -> None:
    handler = httpx.MockTransport(lambda request: httpx.Response(503, json={}))

    with pytest.raises(MaxUnavailableError):
        await build(handler).send(OutboundMessage(chat_id=ChatId(1), text="x"))


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
