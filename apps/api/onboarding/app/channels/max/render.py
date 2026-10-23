"""Domain keyboards to MAX inline keyboards."""

from __future__ import annotations

from typing import Any

from onboarding.core.models import Keyboard


def to_attachments(keyboard: Keyboard) -> list[dict[str, Any]]:
    """An empty keyboard produces no attachment, so a message keeps its default look."""
    if not keyboard:
        return []
    rows = [
        [
            {"type": "callback", "text": button.text, "payload": button.id}
            for button in row
        ]
        for row in keyboard
    ]
    return [{"type": "inline_keyboard", "payload": {"buttons": rows}}]
