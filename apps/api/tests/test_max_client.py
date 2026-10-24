from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

import onboarding.app.channels.max.client as client_module
from onboarding.app.channels.max.client import (
    MaxClient,
    MaxRejectedError,
    MaxUnavailableError,
    Subscription,
)
from onboarding.app.channels.max.files import FileFetchError, MaxFiles
from onboarding.app.channels.max.media import ImageAssetError
from onboarding.app.channels.max.render import to_attachments
from onboarding.app.files.errors import FileTooLargeError
from onboarding.core.models import Address, Button, Channel, ChatId
from onboarding.ports import InboundFile, OutboundMessage

ADDRESS = Address(channel=Channel.MAX, chat_id=ChatId(1))


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
            return httpx.Response(200, json={"photos": {"photoIds": {"token": "media-token"}}})
        messages.append(request)
        return httpx.Response(200, json={"message": {"body": {"mid": "mid-1"}}})

    client = build(httpx.MockTransport(handler), assets_dir=tmp_path)
    message = OutboundMessage(
        address=Address(channel=Channel.MAX, chat_id=ChatId(7)),
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
            return httpx.Response(200, json={"photos": {"photoIds": {"token": "media-token"}}})
        if request.url.path == "/uploads":
            return httpx.Response(200, json={"url": "https://upload.test/image"})
        attempts += 1
        if attempts == 1:
            return httpx.Response(400, json={"code": "attachment.not.ready"})
        return httpx.Response(200, json={"message": {"body": {"mid": "mid-1"}}})

    client = build(httpx.MockTransport(handler), assets_dir=tmp_path)

    mid = await client.send(OutboundMessage(address=ADDRESS, text="x", image="welcome.jpg"))

    assert mid == "mid-1"
    assert attempts == 2


async def test_a_missing_image_fails_before_the_request(tmp_path: Path) -> None:
    client = build(
        httpx.MockTransport(lambda request: httpx.Response(200, json={})), assets_dir=tmp_path
    )

    with pytest.raises(ImageAssetError, match="missing"):
        await client.send(OutboundMessage(address=ADDRESS, text="x", image="ghost.jpg"))


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


def build_files(handler: httpx.MockTransport, max_bytes: int = 1000) -> MaxFiles:
    return MaxFiles(
        client=httpx.AsyncClient(transport=handler),
        token=SecretStr("bot-token"),
        platform_host="platform-api2.max.ru",
        max_bytes=max_bytes,
    )


def test_a_file_is_downloaded_without_sending_the_token_to_a_cdn() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=b"\xff\xd8\xffdata")

    files = build_files(httpx.MockTransport(handler))
    data = asyncio.run(files.fetch(InboundFile(token="t", url="https://cdn.max.ru/f/1")))

    assert data == b"\xff\xd8\xffdata"
    assert seen[0].headers.get("authorization") is None


def test_the_token_rides_along_for_max_itself() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=b"%PDF-1.7")

    files = build_files(httpx.MockTransport(handler))
    asyncio.run(files.fetch(InboundFile(token="t", url="https://platform-api2.max.ru/f/1")))

    assert seen[0].headers["authorization"] == "bot-token"


def test_a_declared_and_a_streamed_file_are_both_capped() -> None:
    declared = httpx.MockTransport(
        lambda request: httpx.Response(200, headers={"content-length": "5000"}, content=b"x")
    )
    streamed = httpx.MockTransport(lambda request: httpx.Response(200, content=b"x" * 5000))

    with pytest.raises(FileTooLargeError):
        asyncio.run(build_files(declared).fetch(InboundFile(token="t", url="https://cdn.max.ru/f")))
    with pytest.raises(FileTooLargeError):
        asyncio.run(build_files(streamed).fetch(InboundFile(token="t", url="https://cdn.max.ru/f")))


def test_a_live_media_host_is_fetched_without_the_token() -> None:
    """Measured 2026-10-24: MAX answers `payload.url` on `fd.oneme.ru`, not on `max.ru`.

    The first live document died here with `untrusted_host`, so the host family is pinned.
    """
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=b"%PDF-1.7")

    files = build_files(httpx.MockTransport(handler))
    for url in (
        "https://fd.oneme.ru/f/1",
        "https://iu.oneme.ru/uploadImage?r=signed",
        "https://i.oneme.ru/i?r=signed",
        "https://oneme.ru/f/1",
    ):
        assert asyncio.run(files.fetch(InboundFile(token="t", url=url))) == b"%PDF-1.7"
    assert seen
    assert all(request.headers.get("authorization") is None for request in seen)


def test_a_lookalike_of_the_media_domain_is_refused() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=b"%PDF-1.7")

    files = build_files(httpx.MockTransport(handler))
    for url in (
        "https://oneme.ru.evil.test/f/1",
        "https://evil-oneme.ru/f/1",
        "https://max.ru.evil.test/f/1",
    ):
        with pytest.raises(FileFetchError, match="untrusted_host"):
            asyncio.run(files.fetch(InboundFile(token="t", url=url)))
    assert seen == []


def test_an_attachment_url_outside_max_is_not_fetched() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=b"%PDF-1.7")

    files = build_files(httpx.MockTransport(handler))

    with pytest.raises(FileFetchError, match="untrusted_host"):
        asyncio.run(files.fetch(InboundFile(token="t", url="http://169.254.169.254/latest")))
    with pytest.raises(FileFetchError, match="untrusted_host"):
        asyncio.run(files.fetch(InboundFile(token="t", url="https://evil.test/x.pdf")))
    assert seen == []


def test_a_missing_url_and_a_bad_status_are_named() -> None:
    files = build_files(httpx.MockTransport(lambda request: httpx.Response(404, content=b"{}")))

    with pytest.raises(FileFetchError, match="no_url"):
        asyncio.run(files.fetch(InboundFile(token="t")))
    with pytest.raises(FileFetchError, match="status_404"):
        asyncio.run(files.fetch(InboundFile(token="t", url="https://cdn.max.ru/f")))
