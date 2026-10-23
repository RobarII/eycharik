"""The Telegram adapter against a recorded transport: shapes and failure classes, no network."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from onboarding.app.channels.profiles import ChannelProfileLibrary
from onboarding.app.channels.telegram.client import (
    TelegramClient,
    TelegramRejectedError,
    TelegramUnavailableError,
)
from onboarding.core.channels import ChannelProfile
from onboarding.core.models import Address, Button, Channel, ChatId
from onboarding.ports import OutboundMessage

ROOT = Path(__file__).resolve().parents[3]
# The shipped profile, not a hand-built one: the adapter is tested against what a deployment loads.
SHIPPED = ChannelProfileLibrary(
    ROOT / "apps" / "api" / "channel-profiles",
    ROOT / "docs" / "contracts" / "channel-profile.schema.json",
).load(Channel.TELEGRAM)
ADDRESS = Address(channel=Channel.TELEGRAM, chat_id=ChatId(111))


def build(
    handler: httpx.MockTransport, profile: ChannelProfile | None = None
) -> TelegramClient:
    return TelegramClient(
        base_url="https://telegram.test",
        token=SecretStr("bot-token"),
        client=httpx.AsyncClient(transport=handler),
        profile=profile or SHIPPED,
    )


def ok(message_id: int = 7) -> httpx.MockTransport:
    return httpx.MockTransport(
        lambda request: httpx.Response(200, json={"ok": True, "result": {"message_id": message_id}})
    )


async def test_send_posts_chat_id_and_the_escaped_text() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 9}})

    message_id = await build(httpx.MockTransport(handler)).send(
        OutboundMessage(address=ADDRESS, text="Отпуск — 28 дней. Точка!")
    )

    body = json.loads(seen[0].content)
    assert seen[0].url.path == "/botbot-token/sendMessage"
    assert body["chat_id"] == 111
    assert body["text"] == "Отпуск — 28 дней\\. Точка\\!"
    assert body["parse_mode"] == "MarkdownV2"
    assert message_id == "9"


async def test_a_keyboard_becomes_an_inline_keyboard() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 9}})

    keyboard = ((Button(id="a", text="Дальше"), Button(id="b", text="Позже")),)
    await build(httpx.MockTransport(handler)).send(
        OutboundMessage(address=ADDRESS, text="x", keyboard=keyboard)
    )

    assert json.loads(seen[0].content)["reply_markup"] == {
        "inline_keyboard": [
            [{"callback_data": "a", "text": "Дальше"}, {"callback_data": "b", "text": "Позже"}]
        ]
    }


async def test_a_profile_without_markup_sends_plain_text() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 9}})

    profile = ChannelProfile(channel=Channel.TELEGRAM, markup="none")
    await build(httpx.MockTransport(handler), profile).send(
        OutboundMessage(address=ADDRESS, text="Отпуск — 28 дней.")
    )

    body = json.loads(seen[0].content)
    assert body["text"] == "Отпуск — 28 дней."
    assert "parse_mode" not in body


async def test_edit_posts_to_edit_message_text() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True, "result": True})

    await build(httpx.MockTransport(handler)).edit(ADDRESS, "5", "Новый текст")

    assert seen[0].url.path == "/botbot-token/editMessageText"
    assert json.loads(seen[0].content)["message_id"] == 5


async def test_a_429_is_retryable() -> None:
    handler = httpx.MockTransport(lambda request: httpx.Response(429, json={}))

    with pytest.raises(TelegramUnavailableError):
        await build(handler).send(OutboundMessage(address=ADDRESS, text="x"))


async def test_a_400_is_rejected_and_carries_the_description() -> None:
    handler = httpx.MockTransport(
        lambda request: httpx.Response(
            400, json={"ok": False, "description": "Bad Request: chat not found"}
        )
    )

    with pytest.raises(TelegramRejectedError, match="chat not found"):
        await build(handler).send(OutboundMessage(address=ADDRESS, text="x"))


async def test_a_transport_failure_is_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    with pytest.raises(TelegramUnavailableError):
        await build(httpx.MockTransport(handler)).send(OutboundMessage(address=ADDRESS, text="x"))


async def test_the_token_never_leaks_into_an_error() -> None:
    handler = httpx.MockTransport(lambda request: httpx.Response(401, json={}))

    with pytest.raises(TelegramRejectedError) as caught:
        await build(handler).send(OutboundMessage(address=ADDRESS, text="x"))

    assert "bot-token" not in str(caught.value)


async def test_the_response_without_a_message_id_is_an_adapter_bug() -> None:
    handler = httpx.MockTransport(lambda request: httpx.Response(200, json={"ok": True}))

    with pytest.raises(RuntimeError, match="message_id"):
        await build(handler).send(OutboundMessage(address=ADDRESS, text="x"))


async def test_set_webhook_sends_the_secret() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True, "result": True})

    await build(httpx.MockTransport(handler)).set_webhook(
        "https://bot.test/webhook/telegram", SecretStr("hook-secret")
    )

    body = json.loads(seen[0].content)
    assert body == {"url": "https://bot.test/webhook/telegram", "secret_token": "hook-secret"}
