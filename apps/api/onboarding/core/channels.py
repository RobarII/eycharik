"""What one messenger can carry, applied without I/O.

A channel profile is data (``apps/api/channel-profiles/<channel>.yaml``, validated against
``docs/contracts/channel-profile.schema.json``). The functions here are the only place that reads
one, and they are pure: splitting and validation are decisions, not transport (ADR 0019).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal

from onboarding.core.models import MAX_MESSAGE_CHARS, Channel, Keyboard

Markup = Literal["none", "markdown", "markdownv2", "html"]
KeyboardScope = Literal["message", "dialog"]


class ChannelProfileError(ValueError):
    """A profile, or a message rendered against it, violates the channel contract."""


@dataclass(frozen=True, slots=True)
class ChannelProfile:
    """Limits and shapes of one messenger. Defaults describe the strictest channel we support."""

    channel: Channel
    max_text_chars: int = MAX_MESSAGE_CHARS
    max_keyboard_rows: int = 3
    max_buttons_per_row: int = 3
    # ``None`` means the channel documents no payload limit, so none is invented here.
    callback_payload_bytes: int | None = None
    keyboard_scope: KeyboardScope = "message"
    supports_image: bool = True
    supports_edit: bool = True
    markup: Markup = "none"
    messages_per_second: float = 2.0
    per_chat_per_second: float | None = None

    def validate(self) -> None:
        if self.max_text_chars <= 0:
            raise ChannelProfileError(f"{self.channel}: max_text_chars must be positive")
        if self.max_text_chars > MAX_MESSAGE_CHARS:
            raise ChannelProfileError(
                f"{self.channel}: max_text_chars {self.max_text_chars} exceeds the domain cap "
                f"{MAX_MESSAGE_CHARS}; a scenario step must be renderable everywhere"
            )
        if self.max_keyboard_rows <= 0 or self.max_buttons_per_row <= 0:
            raise ChannelProfileError(f"{self.channel}: a keyboard needs rows and buttons")
        if self.callback_payload_bytes is not None and self.callback_payload_bytes <= 0:
            raise ChannelProfileError(f"{self.channel}: callback_payload_bytes must be positive")
        if self.messages_per_second <= 0:
            raise ChannelProfileError(f"{self.channel}: messages_per_second must be positive")
        if self.per_chat_per_second is not None and self.per_chat_per_second <= 0:
            raise ChannelProfileError(f"{self.channel}: per_chat_per_second must be positive")

    def fits(self, text: str) -> bool:
        return len(text) <= self.max_text_chars


_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
_SENTENCE_BREAK = re.compile(r"(?<=[.!?…])\s+")


def fit_text(text: str, profile: ChannelProfile) -> tuple[str, ...]:
    """Split one body into parts that fit, at paragraph then sentence boundaries.

    Nothing is dropped and nothing is reordered: the parts, joined by a space, are the same words.
    A single word longer than the limit is cut, because refusing the message would be worse.
    """
    limit = profile.max_text_chars
    if len(text) <= limit:
        return (text,)

    parts: list[str] = []
    for unit in _units(text, limit):
        if parts and len(parts[-1]) + 1 + len(unit) <= limit:
            parts[-1] = f"{parts[-1]} {unit}"
        else:
            parts.append(unit)
    for part in parts:
        if len(part) > limit:
            raise ChannelProfileError(
                f"{profile.channel}: a part of {len(part)} characters exceeds {limit}"
            )
    return tuple(parts)


def _units(text: str, limit: int) -> Iterator[str]:
    for raw_paragraph in _PARAGRAPH_BREAK.split(text):
        paragraph = raw_paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= limit:
            yield paragraph
            continue
        for raw_sentence in _SENTENCE_BREAK.split(paragraph):
            sentence = raw_sentence.strip()
            if not sentence:
                continue
            if len(sentence) <= limit:
                yield sentence
            else:
                yield from _split_words(sentence, limit)


def _split_words(text: str, limit: int) -> Iterator[str]:
    line = ""
    for word in text.split():
        if len(word) > limit:
            if line:
                yield line
                line = ""
            yield from (word[index : index + limit] for index in range(0, len(word), limit))
            continue
        if line and len(line) + 1 + len(word) > limit:
            yield line
            line = word
        else:
            line = f"{line} {word}" if line else word
    if line:
        yield line


def fit_keyboard(keyboard: Keyboard, profile: ChannelProfile) -> Keyboard:
    """Return the keyboard unchanged, or raise: a channel never gets a shape it cannot draw.

    Refusing at load time keeps the failure in the catalog instead of in a dispatcher retry loop.
    """
    if len(keyboard) > profile.max_keyboard_rows:
        raise ChannelProfileError(
            f"{profile.channel}: {len(keyboard)} keyboard rows, at most "
            f"{profile.max_keyboard_rows} supported"
        )
    for row in keyboard:
        if len(row) > profile.max_buttons_per_row:
            raise ChannelProfileError(
                f"{profile.channel}: {len(row)} buttons in a row, at most "
                f"{profile.max_buttons_per_row} supported"
            )
        if profile.callback_payload_bytes is not None:
            for button in row:
                payload = len(button.id.encode("utf-8"))
                if payload > profile.callback_payload_bytes:
                    raise ChannelProfileError(
                        f"{profile.channel}: button id {button.id!r} is {payload} bytes, at most "
                        f"{profile.callback_payload_bytes} supported"
                    )
    return keyboard
