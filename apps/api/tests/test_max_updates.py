from __future__ import annotations

from datetime import UTC, datetime

from onboarding.app.channels.max.ingress import parse_update
from onboarding.core.models import ChatId, EventKind

RECEIVED = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)

MESSAGE_CREATED = {
    "update_type": "message_created",
    "timestamp": 1_760_000_000_000,
    "chat_id": 111,
    "user": {"user_id": 222, "name": "Иван"},
    "message": {
        "sender": {"user_id": 222},
        "recipient": {"chat_id": 111},
        "body": {"mid": "mid-1", "seq": 1, "text": "  Сколько дней отпуска?  "},
    },
}

MESSAGE_CALLBACK = {
    "update_type": "message_callback",
    "timestamp": 1_760_000_000_000,
    "chat_id": 111,
    "callback": {"payload": "documents_done"},
}


def test_parses_a_message() -> None:
    update = parse_update(MESSAGE_CREATED, received_at=RECEIVED)

    assert update is not None
    assert update.event_id == "mid-1"
    assert update.chat_id == ChatId(111)
    assert update.user_id == 222
    assert update.event.kind is EventKind.MESSAGE_RECEIVED
    assert update.event.text == "Сколько дней отпуска?"
    assert update.event.at == datetime(2025, 10, 9, 8, 53, 20, tzinfo=UTC)


def test_parses_a_callback_button() -> None:
    update = parse_update(MESSAGE_CALLBACK, received_at=RECEIVED)

    assert update is not None
    assert update.event.kind is EventKind.BUTTON_PRESSED
    assert update.event.button_id == "documents_done"


def test_ignores_unrelated_update_types() -> None:
    assert parse_update({"update_type": "bot_added"}, received_at=RECEIVED) is None


def test_ignores_a_payload_without_a_chat() -> None:
    payload = {"update_type": "message_created", "timestamp": 1, "message": {"body": {}}}

    assert parse_update(payload, received_at=RECEIVED) is None


def test_empty_text_becomes_none() -> None:
    payload = {
        **MESSAGE_CREATED,
        "message": {"body": {"mid": "mid-2", "text": "   "}},
    }

    update = parse_update(payload, received_at=RECEIVED)

    assert update is not None
    assert update.event.text is None


def test_synthetic_id_is_stable_without_a_mid() -> None:
    payload = {
        "update_type": "message_callback",
        "timestamp": 5,
        "chat_id": 111,
        "callback": {"payload": "x"},
    }

    first = parse_update(payload, received_at=RECEIVED)
    second = parse_update(payload, received_at=RECEIVED)

    assert first is not None
    assert second is not None
    assert first.event_id == second.event_id
    assert first.event_id.startswith("message_callback:111:")


def test_missing_button_payload_keeps_the_event() -> None:
    payload = {"update_type": "message_callback", "timestamp": 5, "chat_id": 111}

    update = parse_update(payload, received_at=RECEIVED)

    assert update is not None
    assert update.event.kind is EventKind.BUTTON_PRESSED
    assert update.event.button_id is None


def test_bot_started_becomes_an_employee_created_event() -> None:
    inbound = parse_update(
        {
            "update_type": "bot_started",
            "timestamp": 1_700_000_000_000,
            "chat_id": 4242,
            "user": {"user_id": 77},
        },
        received_at=datetime(2026, 10, 23, tzinfo=UTC),
    )

    assert inbound is not None
    assert inbound.chat_id == 4242
    assert inbound.user_id == 77
    assert inbound.event.kind.value == "employee_created"
