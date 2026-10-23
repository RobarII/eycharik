from __future__ import annotations

import pytest

from onboarding.api.cursor import CursorError, decode, encode


def test_a_cursor_round_trips_and_is_url_safe() -> None:
    payload = {"at": "2026-10-23T09:00:00+00:00", "run_id": "0f0a6f4e-1b1c-4a58-9d1e-7d6f2a1f9b3c"}

    encoded = encode(payload)

    assert decode(encoded) == payload
    assert set(encoded) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")


def test_a_cursor_is_opaque_rather_than_readable() -> None:
    assert "run_id" not in encode({"run_id": "x"})


@pytest.mark.parametrize("value", ["", "not-base64!!", "W10", "bnVsbA"])
def test_a_malformed_cursor_is_rejected(value: str) -> None:
    with pytest.raises(CursorError):
        decode(value)
