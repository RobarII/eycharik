from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from onboarding.core.retention import cutoff, expired, redact_fields

NOW = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)


def test_cutoff_subtracts_the_window() -> None:
    assert cutoff(NOW, 30) == NOW - timedelta(days=30)


def test_a_window_shorter_than_a_day_is_refused() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        cutoff(NOW, 0)


def test_expired_is_strictly_older_than_the_window() -> None:
    assert expired(NOW - timedelta(days=31), NOW, 30)
    assert not expired(NOW - timedelta(days=30), NOW, 30)


def test_redaction_removes_only_personal_fragments() -> None:
    fields = {
        "employee_id": "1001",
        "level": "high",
        "tags": ["manager"],
        "evidence": [{"text": "руководитель не отвечает"}],
        "quote": "руководитель не отвечает",
    }

    cleaned = redact_fields(fields)

    assert cleaned == {
        "employee_id": "1001",
        "level": "high",
        "tags": ["manager"],
        "redacted": True,
    }


def test_redaction_is_idempotent_and_keeps_clean_rows_unchanged() -> None:
    clean = {"employee_id": "1001", "level": "medium"}

    assert redact_fields(clean) == clean
    assert redact_fields(redact_fields({"employee_id": "1", "quote": "q"})) == {
        "employee_id": "1",
        "redacted": True,
    }
