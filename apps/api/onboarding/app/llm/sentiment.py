"""Parse the sentiment classifier output.

The model labels one answer; the risk level and the escalation decision are computed by
``core/risk.py``. Parsing here is strict for the same reason as ``output.py``: model output is
untrusted, and a malformed label must degrade to the keyword fallback, not to a silent guess.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from onboarding.app.llm.output import AnswerFormatError, parse_json_object
from onboarding.core.models import Sentiment, SignalTag

MAX_TAGS = 3
MAX_REASON_CHARS = 200
_TAGS = {tag.value: tag for tag in SignalTag}


class SentimentFormatError(AnswerFormatError):
    """The model did not honour the sentiment contract."""


@dataclass(frozen=True, slots=True)
class SentimentDraft:
    sentiment: Sentiment
    tags: tuple[SignalTag, ...]
    confidence: float
    reason: str


def parse_sentiment(text: str) -> SentimentDraft:
    payload = parse_json_object(text)
    sentiment = _sentiment(payload)
    tags = _tags(payload)
    confidence = _confidence(payload)
    reason = _reason(payload)
    return SentimentDraft(sentiment=sentiment, tags=tags, confidence=confidence, reason=reason)


def _sentiment(payload: dict[str, Any]) -> Sentiment:
    value = payload.get("sentiment")
    try:
        return Sentiment(str(value))
    except ValueError:
        raise SentimentFormatError(f"unknown sentiment {value!r}") from None


def _tags(payload: dict[str, Any]) -> tuple[SignalTag, ...]:
    value = payload.get("tags")
    if not isinstance(value, list) or not value:
        raise SentimentFormatError("tags must be a non-empty list")
    if len(value) > MAX_TAGS:
        raise SentimentFormatError(f"tags must contain at most {MAX_TAGS} items")
    tags: list[SignalTag] = []
    for item in value:
        tag = _TAGS.get(str(item))
        if tag is None:
            raise SentimentFormatError(f"unknown tag {item!r}")
        if tag not in tags:
            tags.append(tag)
    return tuple(tags)


def _confidence(payload: dict[str, Any]) -> float:
    value = payload.get("confidence")
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise SentimentFormatError("confidence must be a number")
    if not 0.0 <= float(value) <= 1.0:
        raise SentimentFormatError("confidence must be within [0, 1]")
    return float(value)


def _reason(payload: dict[str, Any]) -> str:
    value = payload.get("reason")
    if not isinstance(value, str) or not value.strip():
        raise SentimentFormatError("reason must be a non-empty string")
    if len(value) > MAX_REASON_CHARS:
        raise SentimentFormatError(f"reason exceeds {MAX_REASON_CHARS} characters")
    return value.strip()
