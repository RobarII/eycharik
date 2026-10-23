"""The TypeSafe Jev adapter: rubric loading, strict probabilities, keyword fallback."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from pydantic import SecretStr

from onboarding.app.llm.jev import (
    JevFormatError,
    JevSentimentClassifier,
    JevUnavailableError,
    load_rubric,
    parse_jev,
)
from onboarding.core.models import Sentiment, SignalTag

from .fakes import RecordingAudit

ROOT = Path(__file__).resolve().parents[3]
RUBRIC = ROOT / "docs" / "prompts" / "sentiment-jev" / "v1.yaml"


def answers(
    *,
    choice: str = "negative",
    probabilities: dict[str, float] | None = None,
    noul: dict[str, float] | None = None,
    confidence: float | None = 0.82,
) -> dict[str, Any]:
    sentiment: dict[str, Any] = {
        "type": "choice",
        "choice": choice,
        "probabilities": probabilities
        or {"positive": 0.05, "neutral": 0.15, "negative": 0.80, "unknown": 0.0},
    }
    if confidence is not None:
        sentiment["confidence"] = confidence
    body: dict[str, Any] = {"sentiment": sentiment}
    tags = {key: 0.0 for key in load_rubric(RUBRIC).questions if key.startswith("tag_")}
    tags.update(noul if noul is not None else {"tag_access": 0.91, "tag_it": 0.88})
    for key, value in tags.items():
        body[key] = {"type": "noul", "noul": value}
    return {"model": "jev-1.13.0", "answers": body, "usage": {"input_tokens": 100}}


def test_loads_the_versioned_rubric() -> None:
    rubric = load_rubric(RUBRIC)

    assert rubric.model == "jev-1.13.0"
    assert rubric.version == 1
    assert rubric.questions["sentiment"].criteria == (
        "positive",
        "neutral",
        "negative",
        "unknown",
    )
    assert rubric.questions["tag_access"].type == "noul"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda body: body.update(name="other"),
        lambda body: body.update(version=2),
        lambda body: body.update(model=""),
        lambda body: body.update(tag_threshold=1.5),
        lambda body: body.update(max_tags=9),
        lambda body: body.update(questions={}),
        lambda body: body["questions"].update(sentiment={"type": "noul", "instructions": "?"}),
        lambda body: body["questions"].update(tag_unknown={"type": "noul", "instructions": "?"}),
        lambda body: body["questions"].update(broken={"type": "ranking", "instructions": "?"}),
    ],
)
def test_rejects_a_broken_rubric(mutate: Any, tmp_path: Path) -> None:
    body = yaml.safe_load(RUBRIC.read_text(encoding="utf-8"))
    mutate(body)
    path = tmp_path / "v1.yaml"
    path.write_text(yaml.safe_dump(body, allow_unicode=True), encoding="utf-8")

    with pytest.raises(JevFormatError):
        load_rubric(path)


def test_maps_a_verdict_to_sentiment_and_tags() -> None:
    verdict = parse_jev(answers(), load_rubric(RUBRIC))

    assert verdict.sentiment is Sentiment.NEGATIVE
    assert verdict.tags == (SignalTag.ACCESS, SignalTag.IT)
    assert verdict.confidence == 0.82
    assert verdict.probabilities["negative"] == 0.80


def test_drops_tags_below_the_threshold_and_caps_the_list() -> None:
    body = answers(
        noul={
            "tag_access": 0.9,
            "tag_manager": 0.8,
            "tag_colleagues": 0.7,
            "tag_workload": 0.6,
            "tag_hr": 0.2,
        }
    )

    verdict = parse_jev(body, load_rubric(RUBRIC))

    assert verdict.tags == (SignalTag.ACCESS, SignalTag.MANAGER, SignalTag.COLLEAGUES)


def test_keeps_the_most_likely_tag_when_all_are_below_the_threshold() -> None:
    verdict = parse_jev(answers(noul={"tag_access": 0.3, "tag_it": 0.4}), load_rubric(RUBRIC))

    assert verdict.tags == (SignalTag.IT,)


def test_confidence_defaults_to_the_winning_probability() -> None:
    verdict = parse_jev(answers(confidence=None), load_rubric(RUBRIC))

    assert verdict.confidence == 0.80


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"answers": []},
        {"answers": {}},
        answers(choice="angry"),
        answers(probabilities={"positive": 0.5, "neutral": 0.5, "negative": 0.0, "unknown": 0.0}),
        answers(
            probabilities={"positive": 0.5, "neutral": 0.5, "negative": 0.5, "unknown": 0.0}
        ),
        answers(noul={"tag_access": 1.4}),
        answers(noul={"tag_access": "high"}),
        {"answers": {"sentiment": {"type": "noul", "noul": 0.5}}},
    ],
)
def test_rejects_a_broken_response(body: dict[str, Any]) -> None:
    with pytest.raises(JevFormatError):
        parse_jev(body, load_rubric(RUBRIC))


async def test_sends_the_systemone_request_and_audits_the_verdict() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = request.read().decode()
        return httpx.Response(200, json=answers())

    audit = RecordingAudit()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        classifier = JevSentimentClassifier(
            client=client,
            endpoint="https://api.example.test/v1/systemone",
            api_key=SecretStr("secret"),
            rubric=load_rubric(RUBRIC),
            audit=audit,
        )
        signal = await classifier.classify("Доступ не выдали, третий день", source="day_three")

    assert seen["url"] == "https://api.example.test/v1/systemone"
    assert seen["auth"] == "Bearer secret"
    assert '"model":"jev-1.13.0"' in str(seen["body"])
    assert '"tag_access"' in str(seen["body"])
    assert '"state":"Доступ не выдали, третий день"' in str(seen["body"])
    assert signal.sentiment is Sentiment.NEGATIVE
    assert signal.tags == (SignalTag.ACCESS, SignalTag.IT)
    assert audit.names() == ["sentiment_classified"]
    fields = audit.events[0][1]
    assert fields["provider"] == "jev"
    assert fields["rubric_version"] == 1


async def test_a_server_error_is_retried_then_falls_back_to_keywords() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, json={"error": "overloaded"})

    audit = RecordingAudit()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        classifier = JevSentimentClassifier(
            client=client,
            endpoint="https://api.example.test/v1/systemone",
            api_key=SecretStr("secret"),
            rubric=load_rubric(RUBRIC),
            audit=audit,
            max_retries=1,
        )
        signal = await classifier.classify("Доступ не выдали", source="day_three")

    assert calls == 2
    assert signal.sentiment is Sentiment.NEGATIVE
    assert signal.tags == (SignalTag.ACCESS,)
    assert audit.names() == ["sentiment_fallback"]
    assert audit.events[0][1]["reason"] == "jev_unavailable"


async def test_a_malformed_answer_falls_back_on_the_same_text() -> None:
    body = copy.deepcopy(answers())
    body["answers"]["sentiment"] = {"type": "choice", "choice": "angry"}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    audit = RecordingAudit()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        classifier = JevSentimentClassifier(
            client=client,
            endpoint="https://api.example.test/v1/systemone",
            api_key=SecretStr("secret"),
            rubric=load_rubric(RUBRIC),
            audit=audit,
        )
        signal = await classifier.classify("Доступ не выдали", source="day_three")

    assert signal.sentiment is Sentiment.NEGATIVE
    assert audit.names() == ["sentiment_format_error", "sentiment_fallback"]
    assert audit.events[-1][1]["reason"] == "jev_format"


async def test_a_401_is_not_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(401, json={"error": "bad key"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        classifier = JevSentimentClassifier(
            client=client,
            endpoint="https://api.example.test/v1/systemone",
            api_key=SecretStr("secret"),
            rubric=load_rubric(RUBRIC),
            max_retries=3,
        )
        with pytest.raises(JevUnavailableError):
            await classifier._ask("текст")

    assert calls == 1
