"""Opaque page cursors.

A cursor is the sort key of the last row a page returned, base64url of compact JSON. It is opaque
on purpose: a client must never build one, and changing a sort key later stays a server-side
decision rather than a client-visible contract.
"""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any


class CursorError(ValueError):
    """The cursor is not one we issued. The caller answers 400, never a partial page."""


def encode(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode(value: str) -> dict[str, Any]:
    padded = value + "=" * (-len(value) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (binascii.Error, UnicodeError, ValueError) as error:
        raise CursorError("cursor is not valid") from error
    if not isinstance(payload, dict):
        raise CursorError("cursor is not valid")
    return payload
