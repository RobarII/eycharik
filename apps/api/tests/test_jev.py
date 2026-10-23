"""The TypeSafe Jev adapter: rubric loading, strict probabilities, keyword fallback."""

from __future__ import annotations

import asyncio
import copy
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from pydantic import SecretStr

from onboarding.app.audit import NullAudit
from onboarding.app.clock import FrozenClock
from onboarding.app.llm.jev import (
    JevFormatError,
    JevSentimentClassifier,
    JevUnavailableError,
    parse_jev,
)
from onboarding.app.llm.profiles import classify_profile
from onboarding.app.llm.rubric import Rubric, RubricError, RubricLibrary
from onboarding.app.settings import Settings
from onboarding.core.breaker import CircuitBreaker
from onboarding.core.models import Sentiment, SignalTag
from onboarding.ports import ClassifyProfile

from .conftest import NOW
from .fakes import RecordingAudit

ROOT = Path(__file__).resolve().parents[3]
PROMPTS = ROOT / "docs" / "prompts"
CONTRACTS = ROOT / "docs" / "contracts"
PROFILE = ClassifyProfile(
    name="jev-test",
    model="jev-1.13.0",
    rubric="sentiment-jev@1",
    timeout_s=8.0,
    max_retries=1,
    price_input_rub_per_1k=0.4,
)


def rubrics(root: Path = PROMPTS) -> RubricLibrary:
    return RubricLibrary(root, CONTRACTS / "jev-rubric.schema.json")


def rubric() -> Rubric:
    return rubrics().load("sentiment-jev@1")


async def no_sleep(_: float) -> None:
    return None


def answers(
    *,
    choice: str = "negative",
    probabilities: dict[str, float] | None = None,
    noul: dict[str, float] | None = None,
    confidence: float | None = 0.82,
    usage: int | None = 100,
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
    tags = dict.fromkeys(rubric().tags, 0.0)
    tags.update(noul if noul is not None else {"tag_access": 0.91, "tag_it": 0.88})
    for key, value in tags.items():
        body[key] = {"type": "noul", "noul": value}
    payload: dict[str, Any] = {"model": "jev-1.13.0", "answers": body}
    if usage is not None:
        payload["usage"] = {"input_tokens": usage}
    return payload


def classifier(
    handler: Any,
    *,
    audit: RecordingAudit | None = None,
    profile: ClassifyProfile = PROFILE,
    breaker: CircuitBreaker | None = None,
    rub: Rubric | None = None,
) -> tuple[JevSentimentClassifier, httpx.AsyncClient]:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return (
        JevSentimentClassifier(
            client=client,
            endpoint="https://api.example.test/v1/systemone",
            api_key=SecretStr("secret"),
            profile=profile,
            rubric=rub or rubric(),
            audit=audit,
            clock=FrozenClock(NOW),
            breaker=breaker,
            sleep=no_sleep,
        ),
        client,
    )


def test_loads_the_versioned_rubric() -> None:
    loaded = rubric()

    assert loaded.selector == "sentiment-jev@1"
    assert loaded.questions["sentiment"].criteria == (
        "positive",
        "neutral",
        "negative",
        "unknown",
    )
    assert loaded.questions["tag_access"].type == "noul"


def test_a_later_rubric_version_needs_no_code_change(tmp_path: Path) -> None:
    """The rubric version comes from the file and the selector, never from a constant."""
    source = (PROMPTS / "sentiment-jev" / "v1.yaml").read_text(encoding="utf-8")
    directory = tmp_path / "sentiment-jev"
    directory.mkdir()
    (directory / "v2.yaml").write_text(
        source.replace("version: 1", "version: 2").replace("max_tags: 3", "max_tags: 2"),
        encoding="utf-8",
    )

    loaded = rubrics(tmp_path).load("sentiment-jev@2")

    assert loaded.version == 2
    assert loaded.max_tags == 2


@pytest.mark.parametrize(
    "mutate",
    [
        lambda body: body.update(name="other"),
        lambda body: body.update(version=0),
        lambda body: body.pop("tag_threshold"),
        lambda body: body.update(tag_threshold=1.5),
        lambda body: body.update(max_tags=9),
        lambda body: body.update(extra="silent"),
        lambda body: body.update(questions={}),
        lambda body: body["questions"].update(sentiment={"type": "noul", "instructions": "?"}),
        lambda body: body["questions"].update(tag_unknown={"type": "noul", "instructions": "?"}),
        lambda body: body["questions"].update(broken={"type": "ranking", "instructions": "?"}),
        lambda body: body["questions"]["sentiment"].update(criteria=["positive", "negative"]),
    ],
)
def test_rejects_a_broken_rubric(mutate: Any, tmp_path: Path) -> None:
    body = yaml.safe_load((PROMPTS / "sentiment-jev" / "v1.yaml").read_text(encoding="utf-8"))
    mutate(body)
    directory = tmp_path / "sentiment-jev"
    directory.mkdir()
    (directory / "v1.yaml").write_text(
        yaml.safe_dump(body, allow_unicode=True), encoding="utf-8"
    )

    with pytest.raises(RubricError):
        rubrics(tmp_path).load("sentiment-jev@1")


def test_a_selector_must_match_the_file_it_names(tmp_path: Path) -> None:
    source = (PROMPTS / "sentiment-jev" / "v1.yaml").read_text(encoding="utf-8")
    directory = tmp_path / "sentiment-jev"
    directory.mkdir()
    (directory / "v2.yaml").write_text(source, encoding="utf-8")

    with pytest.raises(RubricError, match="selector"):
        rubrics(tmp_path).load("sentiment-jev@2")
    with pytest.raises(RubricError, match="selector"):
        rubrics(tmp_path).load("sentiment-jev")


def test_maps_a_verdict_to_sentiment_and_tags() -> None:
    verdict = parse_jev(answers(), rubric())

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

    verdict = parse_jev(body, rubric())

    assert verdict.tags == (SignalTag.ACCESS, SignalTag.MANAGER, SignalTag.COLLEAGUES)


def test_keeps_the_most_likely_tag_when_all_are_below_the_threshold() -> None:
    verdict = parse_jev(answers(noul={"tag_access": 0.3, "tag_it": 0.4}), rubric())

    assert verdict.tags == (SignalTag.IT,)


def test_confidence_defaults_to_the_winning_probability() -> None:
    verdict = parse_jev(answers(confidence=None), rubric())

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
        parse_jev(body, rubric())


async def test_sends_the_systemone_request_and_audits_the_verdict() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = request.read().decode()
        return httpx.Response(200, json=answers())

    audit = RecordingAudit()
    subject, client = classifier(handler, audit=audit)
    async with client:
        signal = await subject.classify("Доступ не выдали, третий день", source="day_three")

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
    assert fields["rubric"] == "sentiment-jev@1"
    assert fields["input_tokens"] == 100
    assert fields["cost_rub"] == pytest.approx(0.1 * 0.4)


async def test_the_breaker_opens_instead_of_spending_every_timeout() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, json={})

    audit = RecordingAudit()
    subject, client = classifier(handler, audit=audit, breaker=CircuitBreaker(threshold=1))
    async with client:
        first = await subject.classify("Доступ не выдали", source="day_three")
        second = await subject.classify("Доступ не выдали", source="day_three")

    assert calls == 1
    assert subject.breaker.is_open
    assert first.sentiment is second.sentiment is Sentiment.NEGATIVE
    assert audit.names() == ["sentiment_fallback", "sentiment_fallback"]


async def test_a_server_error_is_retried_then_falls_back_to_keywords() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, json={"error": "overloaded"})

    audit = RecordingAudit()
    subject, client = classifier(handler, audit=audit)
    async with client:
        signal = await subject.classify("Доступ не выдали", source="day_three")

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
    subject, client = classifier(handler, audit=audit)
    async with client:
        signal = await subject.classify("Доступ не выдали", source="day_three")

    assert signal.sentiment is Sentiment.NEGATIVE
    assert audit.names() == ["sentiment_format_error", "sentiment_fallback"]
    assert audit.events[-1][1]["reason"] == "jev_format"


async def test_an_error_envelope_is_an_outage_not_a_format_error() -> None:
    """OpenRouter refuses a blocked key with ``success: false``; the reason must reach the audit."""
    body = {"success": False, "error": "Access denied by security policy."}

    audit = RecordingAudit()
    subject, client = classifier(lambda _: httpx.Response(200, json=body), audit=audit)
    async with client:
        signal = await subject.classify("Доступ не выдали", source="day_three")

    assert signal.sentiment is Sentiment.NEGATIVE
    assert audit.names() == ["sentiment_fallback"]
    assert audit.events[0][1]["reason"] == "jev_unavailable"
    assert "Access denied" in str(audit.events[0][1]["error"])


async def test_a_401_is_not_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(401, json={"error": "bad key"})

    subject, client = classifier(handler)
    async with client:
        with pytest.raises(JevUnavailableError):
            await subject._ask("текст")

    assert calls == 1


def test_the_profile_selects_the_model_and_the_rubric() -> None:
    settings = Settings(
        _env_file=None,
        classify_profile="jev-1.13.0",
        jev_api_key=SecretStr("k"),
        sentiment_provider="jev",
    )

    profile = classify_profile(settings)

    assert profile.model == "jev-1.13.0"
    assert profile.rubric == "sentiment-jev@1"
    assert profile.timeout_s == 8.0
    assert profile.family == "typesafe-jev"


def test_the_environment_can_override_the_rubric_and_the_envelope() -> None:
    settings = Settings(
        _env_file=None,
        sentiment_rubric="sentiment-jev@2",
        jev_timeout_s=3.0,
        jev_max_retries=0,
        jev_price_input_rub_per_1k=0.25,
    )

    profile = classify_profile(settings)

    assert profile.rubric == "sentiment-jev@2"
    assert profile.timeout_s == 3.0
    assert profile.max_retries == 0
    assert profile.price_input_rub_per_1k == 0.25


async def test_a_bad_key_degrades_without_a_second_request() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, json={"error": "bad request"})

    subject, client = classifier(handler)
    async with client:
        signal = await subject.classify("Доступ не выдали", source="day_three")

    assert calls == 1
    assert signal.sentiment is Sentiment.NEGATIVE


def test_the_classifier_without_an_audit_does_not_need_one() -> None:
    subject = JevSentimentClassifier(
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200))),
        endpoint="https://api.example.test/v1/systemone",
        api_key=SecretStr("secret"),
        profile=PROFILE,
        rubric=rubric(),
        audit=NullAudit(),
        clock=FrozenClock(NOW),
        sleep=asyncio.sleep,
    )

    assert subject.profile.rubric == "sentiment-jev@1"
