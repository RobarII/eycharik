from __future__ import annotations

from datetime import UTC, datetime

import pytest

from onboarding.core.quiet_hours import QuietHours

NIGHT = QuietHours(start_hour=21, end_hour=9, timezone="Europe/Moscow")


def utc(hour: int, minute: int = 0, day: int = 24) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=UTC)


def test_a_daytime_message_goes_out_immediately() -> None:
    moment = utc(9)  # 12:00 in Moscow

    assert NIGHT.next_allowed(moment) == moment


def test_a_night_message_waits_until_morning_in_local_time() -> None:
    moment = utc(23)  # 02:00 in Moscow

    allowed = NIGHT.next_allowed(moment)

    assert allowed == datetime(2026, 10, 25, 6, 0, tzinfo=UTC)  # 09:00 Moscow


def test_the_evening_edge_still_counts_as_quiet() -> None:
    moment = datetime(2026, 10, 24, 18, 5, tzinfo=UTC)  # 21:05 Moscow

    assert NIGHT.next_allowed(moment) == datetime(2026, 10, 25, 6, 0, tzinfo=UTC)


def test_a_naive_moment_is_read_as_utc() -> None:
    moment = datetime(2026, 10, 24, 23, 0, tzinfo=UTC).replace(tzinfo=None)

    assert NIGHT.next_allowed(moment) == datetime(2026, 10, 25, 6, 0, tzinfo=UTC)


def test_an_empty_window_is_a_configuration_error() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        QuietHours(start_hour=9, end_hour=9)


def test_an_unknown_timezone_is_a_configuration_error() -> None:
    with pytest.raises(ValueError, match="timezone"):
        QuietHours(start_hour=21, end_hour=9, timezone="Mars/Olympus")
