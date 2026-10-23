"""Telegram payloads to typed inbound messages, including the ones we must ignore."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from pydantic import SecretStr

from onboarding.app.channels.telegram.ingress import SECRET_HEADER, TelegramIngress
from onboarding.core.models import Address, Channel, ChatId, EventKind

NOW = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)
HEADERS = {SECRET_HEADER: "hook-secret"}


def ingress() -> TelegramIngress:
    return TelegramIngress(SecretStr("hook-secret"))


def message(text: str | None = "/start", **extra: object) -> bytes:
    body: dict[str, object] = {
        "message_id": 5,
        "date": 1_760_000_000,
        "chat": {"id": 111, "type": "private"},
        "from": {"id": 222, "is_bot": False, "first_name": "Аня"},
        **extra,
    }
    if text is not None:
        body["text"] = text
    return json.dumps({"update_id": 100, "message": body}).encode()


def test_verify_compares_the_secret_token_header() -> None:
    assert ingress().verify(HEADERS, message())
    assert not ingress().verify({SECRET_HEADER: "wrong"}, message())
    assert not ingress().verify({}, message())
    assert not TelegramIngress(SecretStr("")).verify({SECRET_HEADER: ""}, message())


def test_an_unconfigured_secret_is_not_a_configured_channel() -> None:
    assert not TelegramIngress(SecretStr("")).configured
    assert ingress().configured


def test_telegram_has_no_handshake() -> None:
    assert ingress().handshake(message()) is None


def test_start_becomes_a_first_contact_that_starts_a_run() -> None:
    inbound = ingress().parse(message("/start"), received_at=NOW)

    assert inbound is not None
    assert inbound.starts_run
    assert inbound.event.kind is EventKind.EMPLOYEE_CREATED
    assert inbound.dedupe_key == "telegram:100"
    assert inbound.address == Address(channel=Channel.TELEGRAM, chat_id=ChatId(111))


def test_a_question_is_a_message_with_its_text() -> None:
    inbound = ingress().parse(message("  Сколько дней отпуска?  "), received_at=NOW)

    assert inbound is not None
    assert not inbound.starts_run
    assert inbound.event.kind is EventKind.MESSAGE_RECEIVED
    assert inbound.event.text == "Сколько дней отпуска?"


def test_a_callback_is_a_button_press_on_the_same_address() -> None:
    body = json.dumps(
        {
            "update_id": 101,
            "callback_query": {
                "id": "cb-1",
                "from": {"id": 222, "is_bot": False},
                "data": "docs_ready",
                "message": {
                    "message_id": 6,
                    "date": 1_760_000_000,
                    "chat": {"id": 111, "type": "private"},
                },
            },
        }
    ).encode()

    inbound = ingress().parse(body, received_at=NOW)

    assert inbound is not None
    assert inbound.event.kind is EventKind.BUTTON_PRESSED
    assert inbound.event.button_id == "docs_ready"
    assert inbound.address.chat_id == ChatId(111)
    assert inbound.dedupe_key == "telegram:101"


def test_a_document_is_a_file_with_an_id() -> None:
    body = message(
        None, document={"file_id": "file-1", "file_unique_id": "unique-1", "file_name": "c.pdf"}
    )

    inbound = ingress().parse(body, received_at=NOW)

    assert inbound is not None
    assert inbound.event.kind is EventKind.FILE_RECEIVED
    assert inbound.event.file_id == "unique-1"


def test_the_date_of_the_message_wins_over_the_arrival_time() -> None:
    inbound = ingress().parse(message("привет"), received_at=NOW)

    assert inbound is not None
    assert inbound.event.at.tzinfo is UTC
    assert inbound.event.at.year == 2025


def test_an_update_without_an_id_or_a_chat_is_ignored() -> None:
    assert ingress().parse(b'{"message": {}}', received_at=NOW) is None
    no_sender = b'{"update_id": 1, "message": {"chat": {"id": 1}}}'
    assert ingress().parse(no_sender, received_at=NOW) is None
    assert ingress().parse(b"not json", received_at=NOW) is None
