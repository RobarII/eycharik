"""VK Callback API payloads: the confirmation handshake, `ok` dedupe keys, and buttons."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from pydantic import SecretStr

from onboarding.app.channels.vk.ingress import VkIngress
from onboarding.core.models import Address, Channel, ChatId, EventKind

NOW = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)


def ingress() -> VkIngress:
    return VkIngress(SecretStr("vk-secret"), SecretStr("confirm-code"))


def body(payload: dict[str, object]) -> bytes:
    return json.dumps({"secret": "vk-secret", "group_id": 1, **payload}).encode()


def new_message(text: str | None = "привет", **extra: object) -> bytes:
    message: dict[str, object] = {
        "peer_id": 2000000001,
        "from_id": 777,
        "date": 1_760_000_000,
        **extra,
    }
    if text is not None:
        message["text"] = text
    return body({"type": "message_new", "event_id": "evt-1", "object": {"message": message}})


def test_verify_reads_the_secret_from_the_payload() -> None:
    assert ingress().verify({}, new_message())
    assert not ingress().verify({}, b'{"secret": "wrong", "type": "message_new"}')
    assert not ingress().verify({}, b"{}")
    assert not VkIngress(SecretStr(""), SecretStr("c")).verify({}, new_message())


def test_a_confirmation_handshake_needs_both_secrets() -> None:
    assert not VkIngress(SecretStr("vk-secret"), SecretStr("")).configured
    assert ingress().configured


def test_confirmation_is_answered_with_the_code() -> None:
    assert ingress().handshake(b'{"type": "confirmation"}') == "confirm-code"
    assert ingress().handshake(new_message()) is None


def test_start_becomes_a_first_contact_that_starts_a_run() -> None:
    inbound = ingress().parse(new_message("/start"), received_at=NOW)

    assert inbound is not None
    assert inbound.starts_run
    assert inbound.event.kind is EventKind.EMPLOYEE_CREATED
    assert inbound.dedupe_key == "vk:evt-1"
    assert inbound.address == Address(channel=Channel.VK, chat_id=ChatId(2000000001))
    assert inbound.sender == "777"


def test_a_question_keeps_its_text() -> None:
    inbound = ingress().parse(new_message("  Где взять пропуск?  "), received_at=NOW)

    assert inbound is not None
    assert inbound.event.kind is EventKind.MESSAGE_RECEIVED
    assert inbound.event.text == "Где взять пропуск?"


def test_a_callback_button_carries_the_payload_id() -> None:
    payload = body(
        {
            "type": "message_event",
            "event_id": "evt-2",
            "object": {
                "peer_id": 2000000001,
                "user_id": 777,
                "event_id": "cb-1",
                "payload": json.dumps({"id": "docs_ready"}),
            },
        }
    )

    inbound = ingress().parse(payload, received_at=NOW)

    assert inbound is not None
    assert inbound.event.kind is EventKind.BUTTON_PRESSED
    assert inbound.event.button_id == "docs_ready"
    assert inbound.dedupe_key == "vk:evt-2"


def test_a_document_attachment_is_a_file() -> None:
    attachment = {
        "type": "doc",
        "doc": {"id": 55, "owner_id": 777, "title": "contract.pdf"},
    }

    inbound = ingress().parse(new_message(None, attachments=[attachment]), received_at=NOW)

    assert inbound is not None
    assert inbound.event.kind is EventKind.FILE_RECEIVED
    assert inbound.event.file_id == "55"


def test_the_date_of_the_message_wins_over_the_arrival_time() -> None:
    inbound = ingress().parse(new_message("привет"), received_at=NOW)

    assert inbound is not None
    assert inbound.event.at.tzinfo is UTC
    assert inbound.event.at.year == 2025


def test_an_event_without_an_id_is_ignored() -> None:
    assert ingress().parse(b'{"type": "message_new", "object": {}}', received_at=NOW) is None
    assert ingress().parse(b"not json", received_at=NOW) is None
    assert ingress().parse(b'{"type": "wall_post_new", "event_id": "e"}', received_at=NOW) is None
