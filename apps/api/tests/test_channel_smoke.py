"""The channel smoke fabricates messenger payloads; the real parser must accept them.

A smoke that posts a shape the ingress does not understand proves nothing, and the mismatch would
show up as a timeout on a live host instead of a failing test. So every fabricated update is parsed
here by the same adapter the webhook uses, and the dedupe keys it will produce are pinned down.
"""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from onboarding.app.channels.max.ingress import parse_update
from onboarding.core.models import ChatId, EventKind

RECEIVED = datetime(2026, 10, 24, 9, 0, tzinfo=UTC)
CHAT = 7_000_001
SMOKE = Path(__file__).resolve().parents[3] / "scripts" / "channel_smoke.py"


def _smoke() -> Any:
    spec = importlib.util.spec_from_file_location("channel_smoke", SMOKE)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _updates(smoke: Any, chat_id: int = CHAT) -> Any:
    return smoke.MaxUpdates(http=None, url="https://host/webhook/max", secret="s", chat_id=chat_id)


def test_max_start_is_a_parsed_bot_started() -> None:
    update = parse_update(_updates(_smoke()).payload_start(), received_at=RECEIVED)

    assert update is not None
    assert update.update_type == "bot_started"
    assert update.chat_id == ChatId(CHAT)
    assert update.user_id == CHAT
    assert update.event.kind is EventKind.EMPLOYEE_CREATED


def test_max_message_is_a_parsed_message_with_a_body_id() -> None:
    payload = _updates(_smoke()).payload_message("Привет")
    update = parse_update(payload, received_at=RECEIVED)

    assert update is not None
    assert update.event.kind is EventKind.MESSAGE_RECEIVED
    assert update.event.text == "Привет"
    # An empty text is an empty event, so the caller's message must not arrive as None.
    assert update.event_id == payload["message"]["body"]["mid"]


def test_max_callback_is_a_parsed_button_with_its_own_id() -> None:
    payload = _updates(_smoke()).payload_button("q_tone_formal")
    update = parse_update(payload, received_at=RECEIVED)

    assert update is not None
    assert update.event.kind is EventKind.BUTTON_PRESSED
    assert update.event.button_id == "q_tone_formal"
    assert update.event_id == payload["callback"]["callback_id"]


def test_max_ids_are_unique_enough_for_the_dedupe_table() -> None:
    updates = _updates(_smoke())
    payload = updates.payload_start()

    first = parse_update(payload, received_at=RECEIVED)
    repeat = parse_update(payload, received_at=RECEIVED)
    later = parse_update(updates.payload_start(), received_at=RECEIVED)

    assert first is not None
    assert repeat is not None
    assert later is not None
    # A redelivery has to collapse into one event, or the smoke's dedupe check proves nothing.
    assert first.event_id == repeat.event_id
    # Two starts inside the same millisecond must still be two events: bot_started has no body id,
    # so its key is a hash of the payload, and a shared timestamp would swallow the second start.
    assert later.event_id != first.event_id


def test_max_capabilities_match_what_the_contract_promises() -> None:
    smoke = _smoke()
    max_updates = _updates(smoke)

    assert max_updates.text_limit == 4000
    assert max_updates.secret_header == "X-Max-Bot-Api-Secret"
    # The secret rides in a header, so a broken body is named as such, not refused as unsigned.
    assert max_updates.non_json_status == 400
    assert max_updates.supports_files is False
    assert smoke.Updates.supports_files is True
    assert smoke.VkUpdates.supports_files is True
