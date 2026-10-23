"""Text and keyboard escaping for the channel dialects.

Domain text is written once, in plain Russian, and never in a messenger's markup (ADR 0019). A
renderer escapes it here; the copy file, the knowledge base, and the prompts stay dialect-free.
"""

from __future__ import annotations

from onboarding.core.channels import Markup
from onboarding.core.models import Keyboard

# Telegram MarkdownV2 reserves these outside of entities.
_MARKDOWN_V2_RESERVED = frozenset("_*[]()~`>#+-=|{}.!")


def escape(text: str, markup: Markup) -> str:
    """Make plain text safe for the dialect, losing nothing."""
    if markup == "markdownv2":
        return "".join(f"\\{char}" if char in _MARKDOWN_V2_RESERVED else char for char in text)
    if markup == "html":
        return (
            text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
    return text


def to_reply_markup(
    keyboard: Keyboard, *, field: str = "callback_data"
) -> dict[str, object] | None:
    """The inline keyboard both MAX and Telegram understand, with their own callback field."""
    if not keyboard:
        return None
    rows = [
        [{field: button.id, "text": button.text} for button in row] for row in keyboard
    ]
    return {"inline_keyboard": rows}
