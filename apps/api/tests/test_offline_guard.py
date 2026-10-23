"""The offline tier has to be provable, not promised.

These tests assert the guard itself: an unmarked test cannot open a socket, and the failure names
the marker it should have used. Without them "no tokens in the unit run" is a hope.
"""

from __future__ import annotations

import socket

import httpx
import pytest


async def test_an_unmarked_test_cannot_reach_a_real_endpoint() -> None:
    async with httpx.AsyncClient(timeout=5.0) as client:
        with pytest.raises(AssertionError, match=r"offline test tried to reach example\.com"):
            await client.post("https://example.com/v1/chat/completions", json={})


def test_an_unmarked_test_cannot_open_a_raw_socket() -> None:
    """A library that skips httpx still has to pass the socket layer."""
    with socket.socket() as raw_socket, pytest.raises(
        AssertionError, match="offline test opened a socket"
    ):
        raw_socket.connect(("93.184.216.34", 443))
