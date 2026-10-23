"""The channel contract, checked against every adapter.

A messenger is a value plus two ports (ADR 0019). This module pins the parts a new adapter must
satisfy, so "add Telegram" cannot quietly become "add a branch in the dispatcher".
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx
import pytest
from pydantic import SecretStr

from onboarding.app.channels.max.client import MaxClient
from onboarding.app.channels.max.ingress import MaxIngress
from onboarding.app.channels.telegram.ingress import TelegramIngress
from onboarding.core.channels import ChannelProfile, fit_keyboard, fit_text
from onboarding.core.models import Address, Button, Channel, ChatId
from onboarding.ports import Ingress, Messaging

RECEIVED = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)

MAX_MESSAGE = {
    "update_type": "message_created",
    "timestamp": 1_760_000_000_000,
    "chat_id": 111,
    "user": {"user_id": 222},
    "message": {"body": {"mid": "mid-1", "text": "Сколько дней отпуска?"}},
}

MAX_START = {
    "update_type": "bot_started",
    "timestamp": 1_760_000_000_000,
    "chat_id": 111,
    "user": {"user_id": 222},
}


def max_ingress() -> MaxIngress:
    return MaxIngress(SecretStr("shared-secret"))


def is_ingress(candidate: object) -> bool:
    return isinstance(candidate, Ingress)


def test_a_telegram_ingress_is_an_ingress_too() -> None:
    assert is_ingress(TelegramIngress(SecretStr("hook-secret")))
    assert is_ingress(max_ingress())


def test_every_ingress_namespaces_its_dedupe_key_by_channel() -> None:
    telegram = TelegramIngress(SecretStr("hook-secret"))
    deliveries = {
        Channel.MAX: (max_ingress(), json.dumps(MAX_MESSAGE).encode()),
        Channel.TELEGRAM: (
            telegram,
            json.dumps(
                {
                    "update_id": 7,
                    "message": {
                        "message_id": 1,
                        "date": 1_760_000_000,
                        "chat": {"id": 111},
                        "from": {"id": 222},
                        "text": "привет",
                    },
                }
            ).encode(),
        ),
    }

    keys = {
        channel: ingress.parse(body, received_at=RECEIVED).dedupe_key  # type: ignore[union-attr]
        for channel, (ingress, body) in deliveries.items()
    }

    assert keys[Channel.MAX] == "max:mid-1"
    assert keys[Channel.TELEGRAM] == "telegram:7"


def test_an_ingress_is_verified_by_its_own_secret_header() -> None:
    ingress = max_ingress()

    assert ingress.verify({"x-max-bot-api-secret": "shared-secret"}, b"{}")
    assert not ingress.verify({"x-max-bot-api-secret": "wrong"}, b"{}")
    assert not ingress.verify({}, b"{}")


def test_an_ingress_without_a_secret_is_not_configured() -> None:
    assert not MaxIngress(SecretStr("")).configured
    assert max_ingress().configured


def test_only_vk_answers_a_handshake() -> None:
    assert max_ingress().handshake(b"{}") is None


def test_a_parsed_delivery_is_namespaced_by_channel() -> None:
    inbound = max_ingress().parse(json.dumps(MAX_MESSAGE).encode(), received_at=RECEIVED)

    assert inbound is not None
    assert inbound.dedupe_key == "max:mid-1"
    assert inbound.address == Address(channel=Channel.MAX, chat_id=ChatId(111))
    assert inbound.sender == "222"
    assert not inbound.starts_run


def test_a_first_contact_starts_a_run() -> None:
    inbound = max_ingress().parse(json.dumps(MAX_START).encode(), received_at=RECEIVED)

    assert inbound is not None
    assert inbound.starts_run


def test_an_unknown_update_is_ignored_not_fatal() -> None:
    assert max_ingress().parse(b'{"update_type": "typing"}', received_at=RECEIVED) is None
    assert max_ingress().parse(b"not json", received_at=RECEIVED) is None


def test_parsing_the_same_delivery_twice_is_the_same_value() -> None:
    body = json.dumps(MAX_MESSAGE).encode()

    assert max_ingress().parse(body, received_at=RECEIVED) == max_ingress().parse(
        body, received_at=RECEIVED
    )


def test_a_messenger_implements_the_outbound_port() -> None:
    client = MaxClient(
        base_url="https://max.test",
        token=SecretStr("token"),
        client=httpx.AsyncClient(),
    )

    assert isinstance(client, Messaging)
    assert client.channel is Channel.MAX


def _profile(channel: Channel) -> ChannelProfile:
    return ChannelProfile(channel=channel)


@pytest.mark.parametrize("channel", list(Channel))
def test_every_channel_renders_a_domain_keyboard(channel: Channel) -> None:
    keyboard = ((Button(id="go", text="Дальше"),),)

    assert fit_keyboard(keyboard, _profile(channel)) == keyboard


@pytest.mark.parametrize("channel", list(Channel))
def test_every_channel_can_carry_the_domain_cap(channel: Channel) -> None:
    profile = _profile(channel)
    body = "Первое предложение. " * 400

    parts = fit_text(body, profile)

    assert all(len(part) <= profile.max_text_chars for part in parts)
    assert " ".join(parts) == body.strip()
