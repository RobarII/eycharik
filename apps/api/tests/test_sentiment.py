"""The sentiment contract: what the classifier may return and what is rejected."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from onboarding.app.llm.sentiment import (
    SentimentClassifier,
    SentimentFormatError,
    parse_sentiment,
)
from onboarding.app.prompts import PromptLibrary
from onboarding.core.models import Sentiment, SignalTag
from onboarding.ports import LLMUnavailableError

from .fakes import RecordingAudit, ScriptedLLM


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


ROOT = Path(__file__).resolve().parents[3]


def classifier(responses: list[str | Exception]) -> tuple[SentimentClassifier, RecordingAudit]:
    audit = RecordingAudit()
    return (
        SentimentClassifier(
            llm=ScriptedLLM(responses=list(responses)),
            prompts=PromptLibrary(ROOT / "docs" / "prompts"),
            audit=audit,
        ),
        audit,
    )


async def test_the_model_label_becomes_a_signal() -> None:
    label = json.dumps(
        {
            "sentiment": "negative",
            "tags": ["manager"],
            "risk": "high",
            "confidence": 0.9,
            "reason": "Конфликт с руководителем",
            "escalate_to": "recruiter",
        },
        ensure_ascii=False,
    )
    subject, audit = classifier([label])

    signal = await subject.classify("Начальник кричит при всех", source="survey:manager")

    assert signal.sentiment is Sentiment.NEGATIVE
    assert signal.tags == (SignalTag.MANAGER,)
    assert signal.confidence == 0.9
    assert "sentiment_classified" in audit.names()


@pytest.mark.parametrize(
    "response",
    ["не JSON вовсе", LLMUnavailableError("down")],
)
async def test_a_broken_model_falls_back_to_keywords(response: str | Exception) -> None:
    subject, audit = classifier([response])

    signal = await subject.classify(
        "Руководитель не отвечает, конфликт в команде", source="survey:manager"
    )

    assert signal.sentiment is Sentiment.NEGATIVE
    assert SignalTag.MANAGER in signal.tags
    assert "sentiment_fallback" in audit.names()
