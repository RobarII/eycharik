"""The VK adapter against a recorded transport: form encoding, dialog keyboard, error codes."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from onboarding.app.channels.profiles import ChannelProfileLibrary
from onboarding.app.channels.vk.client import VkClient, VkRejectedError, VkUnavailableError
from onboarding.core.channels import ChannelProfile
from onboarding.core.models import Address, Button, Channel, ChatId
from onboarding.ports import OutboundMessage

ROOT = Path(__file__).resolve().parents[3]
SHIPPED = ChannelProfileLibrary(
    ROOT / "apps" / "api" / "channel-profiles",
    ROOT / "docs" / "contracts" / "channel-profile.schema.json",
).load(Channel.VK)
ADDRESS = Address(channel=Channel.VK, chat_id=ChatId(2000000001))


def build(handler: httpx.MockTransport, profile: ChannelProfile | None = None) -> VkClient:
    return VkClient(
        base_url="https://vk.test",
        api_version="5.199",
        token=SecretStr("vk-token"),
        client=httpx.AsyncClient(transport=handler),
        profile=profile or SHIPPED,
    )


def capture(seen: list[httpx.Request], response: object = 42) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"response": response})

    return httpx.MockTransport(handler)


async def test_send_posts_the_peer_and_a_random_id() -> None:
    seen: list[httpx.Request] = []

    message_id = await build(capture(seen)).send(
        OutboundMessage(address=ADDRESS, text="Сколько дней отпуска?")
    )

    form = dict(httpx.QueryParams(seen[0].content.decode()))
    assert seen[0].url.path == "/method/messages.send"
    assert form["peer_id"] == "2000000001"
    assert form["message"] == "Сколько дней отпуска?"
    assert form["access_token"] == "vk-token"
    assert form["v"] == "5.199"
    assert form["random_id"]
    assert message_id == "42"


async def test_a_keyboard_is_encoded_as_a_callback_dialog() -> None:
    seen: list[httpx.Request] = []

    await build(capture(seen)).send(
        OutboundMessage(address=ADDRESS, text="x", keyboard=((Button(id="go", text="Дальше"),),))
    )

    form = dict(httpx.QueryParams(seen[0].content.decode()))
    keyboard = json.loads(form["keyboard"])
    assert keyboard["one_time"] is False
    assert "inline" not in keyboard
    assert keyboard["buttons"] == [
        [{"action": {"type": "callback", "label": "Дальше", "payload": '{"id": "go"}'}}]
    ]


async def test_a_message_without_buttons_clears_the_dialog_keyboard() -> None:
    seen: list[httpx.Request] = []

    await build(capture(seen)).send(OutboundMessage(address=ADDRESS, text="x"))

    form = dict(httpx.QueryParams(seen[0].content.decode()))
    assert json.loads(form["keyboard"]) == {"buttons": []}


async def test_edit_posts_to_messages_edit() -> None:
    seen: list[httpx.Request] = []

    await build(capture(seen)).edit(ADDRESS, "9", "Новый текст")

    form = dict(httpx.QueryParams(seen[0].content.decode()))
    assert seen[0].url.path == "/method/messages.edit"
    assert form["message_id"] == "9"
    assert form["message"] == "Новый текст"


@pytest.mark.parametrize("code", [1, 6, 9, 10])
async def test_a_documented_retry_code_is_unavailable(code: int) -> None:
    handler = httpx.MockTransport(
        lambda request: httpx.Response(
            200, json={"error": {"error_code": code, "error_msg": "try later"}}
        )
    )

    with pytest.raises(VkUnavailableError):
        await build(handler).send(OutboundMessage(address=ADDRESS, text="x"))


@pytest.mark.parametrize("code", [100, 113])
async def test_a_bad_request_code_is_rejected(code: int) -> None:
    handler = httpx.MockTransport(
        lambda request: httpx.Response(
            200, json={"error": {"error_code": code, "error_msg": "invalid parameter"}}
        )
    )

    with pytest.raises(VkRejectedError, match="invalid parameter"):
        await build(handler).send(OutboundMessage(address=ADDRESS, text="x"))


async def test_a_transport_failure_is_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    with pytest.raises(VkUnavailableError):
        await build(httpx.MockTransport(handler)).send(OutboundMessage(address=ADDRESS, text="x"))


async def test_the_token_never_leaks_into_an_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    with pytest.raises(VkUnavailableError) as caught:
        await build(httpx.MockTransport(handler)).send(OutboundMessage(address=ADDRESS, text="x"))

    assert "vk-token" not in str(caught.value)
