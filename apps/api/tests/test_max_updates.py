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
    assert inbound.starts_run


def test_a_photo_becomes_a_file_event_with_its_token() -> None:
    inbound = parse_update(
        {
            **MESSAGE_CREATED,
            "message": {
                **MESSAGE_CREATED["message"],
                "body": {
                    "mid": "mid-photo",
                    "attachments": [
                        {"type": "image", "payload": {"token": "photo-token-1", "url": "https://x"}}
                    ],
                },
            },
        },
        received_at=RECEIVED,
    )

    assert inbound is not None
    assert inbound.event.kind is EventKind.FILE_RECEIVED
    assert inbound.event.file_id == "photo-token-1"
    assert not inbound.starts_run


def test_a_file_falls_back_to_the_documented_ids() -> None:
    for payload, expected in (
        ({"file_id": "f-1"}, "f-1"),
        ({"photo_id": 42}, "42"),
        ({"url": "https://cdn/x.pdf"}, "https://cdn/x.pdf"),
    ):
        inbound = parse_update(
            {
                **MESSAGE_CREATED,
                "message": {
                    **MESSAGE_CREATED["message"],
                    "body": {
                        "mid": "mid-file",
                        "attachments": [{"type": "file", "payload": payload}],
                    },
                },
            },
            received_at=RECEIVED,
        )

        assert inbound is not None
        assert inbound.event.file_id == expected


def test_a_caption_stays_with_the_file() -> None:
    inbound = parse_update(
        {
            **MESSAGE_CREATED,
            "message": {
                **MESSAGE_CREATED["message"],
                "body": {
                    "mid": "mid-photo-2",
                    "text": " вот паспорт ",
                    "attachments": [{"type": "image", "payload": {"token": "t-2"}}],
                },
            },
        },
        received_at=RECEIVED,
    )

    assert inbound is not None
    assert inbound.event.kind is EventKind.FILE_RECEIVED
    assert inbound.event.text == "вот паспорт"


def test_a_typed_start_command_starts_the_run() -> None:
    # MAX has no command router: the same text arrives as a plain message. It must still open
    # the run, like `/start` does on Telegram and VK.
    inbound = parse_update(
        {
            **MESSAGE_CREATED,
            "message": {
                **MESSAGE_CREATED["message"],
                "body": {"mid": "mid-start", "text": " /start "},
            },
        },
        received_at=RECEIVED,
    )

    assert inbound is not None
    assert inbound.event.kind is EventKind.EMPLOYEE_CREATED
    assert inbound.starts_run


def test_a_message_that_merely_mentions_start_is_a_question() -> None:
    inbound = parse_update(
        {
            **MESSAGE_CREATED,
            "message": {
                **MESSAGE_CREATED["message"],
                "body": {"mid": "mid-2", "text": "как работает /start?"},
            },
        },
        received_at=RECEIVED,
    )

    assert inbound is not None
    assert inbound.event.kind is EventKind.MESSAGE_RECEIVED
    assert not inbound.starts_run
    assert inbound.event.text == "как работает /start?"


# Captured from the live platform on 2026-10-24: a callback has no outer chat_id or user, the
# presser sits in callback.user, and message.sender is the bot that owns the keyboard.
REAL_CALLBACK = {
    "callback": {
        "timestamp": 1_792_832_437_454,
        "callback_id": "callback-abc",
        "user": {"user_id": 502_781_191, "name": "Егор Суровцев"},
        "payload": "tone_you",
    },
    "timestamp": 1_792_832_437_454,
    "message": {
        "recipient": {"chat_type": "dialog", "chat_id": 278_874_685, "user_id": 502_781_191},
        "sender": {"user_id": 224_960_314, "is_bot": True, "name": "Эйчарик"},
        "body": {"mid": "mid-bot-1", "text": "Как вам удобнее общаться?"},
    },
    "user_locale": "en",
    "update_type": "message_callback",
}


def test_parses_a_real_callback_with_the_presser_not_the_bot() -> None:
    update = parse_update(REAL_CALLBACK, received_at=RECEIVED)

    assert update is not None
    assert update.user_id == 502_781_191
    assert update.chat_id == ChatId(278_874_685)
    assert update.event.kind is EventKind.BUTTON_PRESSED
    assert update.event.button_id == "tone_you"
    assert update.event_id == "callback-abc"


def test_each_press_of_the_same_keyboard_is_a_distinct_event() -> None:
    first = parse_update(REAL_CALLBACK, received_at=RECEIVED)
    second = parse_update(
        {**REAL_CALLBACK, "callback": {**REAL_CALLBACK["callback"], "callback_id": "callback-def"}},
        received_at=RECEIVED,
    )

    assert first is not None
    assert second is not None
    assert first.event_id != second.event_id
