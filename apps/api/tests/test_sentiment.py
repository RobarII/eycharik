"""The sentiment contract: what the classifier may return and what is rejected."""

from __future__ import annotations

import json

import pytest

from onboarding.app.llm.sentiment import SentimentFormatError, parse_sentiment
from onboarding.core.models import Sentiment, SignalTag


def payload(**overrides: object) -> str:
    body = {
        "sentiment": "negative",
        "tags": ["access"],
        "risk": "medium",
        "confidence": 0.8,
        "reason": "Доступ не выдали",
        "escalate_to": "none",
    }
    body.update(overrides)
    return json.dumps(body, ensure_ascii=False)


def test_parses_a_valid_label() -> None:
    draft = parse_sentiment(payload())

    assert draft.sentiment is Sentiment.NEGATIVE
    assert draft.tags == (SignalTag.ACCESS,)
    assert draft.confidence == 0.8
    assert draft.reason == "Доступ не выдали"


def test_accepts_a_fenced_json_block() -> None:
    fenced = f"```json\n{payload()}\n```"

    assert parse_sentiment(fenced).sentiment is Sentiment.NEGATIVE


def test_deduplicates_tags_and_keeps_order() -> None:
    draft = parse_sentiment(payload(tags=["it", "access", "it"]))

    assert draft.tags == (SignalTag.IT, SignalTag.ACCESS)


@pytest.mark.parametrize(
    "overrides",
    [
        {"sentiment": "angry"},
        {"tags": []},
        {"tags": ["salary"]},
        {"tags": ["access", "it", "hr", "manager"]},
        {"confidence": 1.5},
        {"reason": "я" * 201},
    ],
)
def test_rejects_a_broken_label(overrides: dict[str, object]) -> None:
    with pytest.raises(SentimentFormatError):
        parse_sentiment(payload(**overrides))
