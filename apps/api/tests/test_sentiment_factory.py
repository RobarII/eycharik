"""One factory, one fallback: the two classifiers must be interchangeable and degrade alike."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from pydantic import SecretStr

from onboarding.app.clock import FrozenClock
from onboarding.app.llm.fallback import MAX_TAGS, KeywordSentiment
from onboarding.app.llm.rubric import RubricLibrary
from onboarding.app.llm.sentiment import (
    SentimentClassifier,
    SentimentSetupError,
    build_sentiment,
)
from onboarding.app.prompts import PromptLibrary
from onboarding.app.settings import REPO_ROOT, Settings
from onboarding.core.models import RiskSignal
from onboarding.ports import LLMUnavailableError

from .conftest import NOW
from .fakes import RecordingAudit, ScriptedLLM

PROMPTS = REPO_ROOT / "docs" / "prompts"
CONTRACTS = REPO_ROOT / "docs" / "contracts"
TEXT = "Руководитель не отвечает, конфликт в команде"


def settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]


def client(handler: Any) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def build(
    provider: str,
    *,
    audit: RecordingAudit | None = None,
    llm: Any = None,
    http: httpx.AsyncClient | None = None,
    **overrides: object,
) -> Any:
    values: dict[str, object] = {"classify_profile": "jev-1.13.0", **overrides}
    return build_sentiment(
        settings(**values),
        clock=FrozenClock(NOW),
        client=http or client(lambda _: httpx.Response(200, json={})),
        prompts=PromptLibrary(PROMPTS),
        audit=audit,
        llm=llm,
        provider=provider,
    )


def jev_answers(choice: str = "negative") -> dict[str, Any]:
    rubric = RubricLibrary(PROMPTS, CONTRACTS / "jev-rubric.schema.json").load(
        "sentiment-jev@1"
    )
    return {
        "answers": {
            "sentiment": {
                "type": "choice",
                "choice": choice,
                "probabilities": {
                    "positive": 0.1,
                    "neutral": 0.1,
                    "negative": 0.8 if choice == "negative" else 0.0,
                    "unknown": 0.0,
                },
            },
            **{key: {"type": "noul", "noul": 0.1} for key in rubric.tags},
        }
    }


def test_the_keyword_provider_needs_no_key_and_no_model() -> None:
    choice = build("keyword")

    assert choice.provider == "keyword"
    assert choice.model == ""
    assert isinstance(choice.classifier, KeywordSentiment)


def test_the_prompt_provider_without_a_key_is_a_setup_error() -> None:
    with pytest.raises(SentimentSetupError, match="LLM_API_KEY"):
        build("prompt")


def test_the_jev_provider_without_a_key_is_a_setup_error() -> None:
    with pytest.raises(SentimentSetupError, match="JEV_API_KEY"):
        build("jev")


def test_the_prompt_provider_names_the_model_it_will_call() -> None:
    choice = build(
        "prompt",
        llm=ScriptedLLM(responses=[]),
        llm_api_key=SecretStr("sk"),
        llm_profile="gigachat-2-pro",
    )

    assert choice.provider == "prompt"
    assert choice.prompt_version == 1
    assert choice.model


def test_the_jev_provider_takes_the_model_and_the_rubric_from_the_profile() -> None:
    choice = build("jev", jev_api_key=SecretStr("jev"))

    assert choice.provider == "jev"
    assert choice.model == "jev-1.13.0"
    assert choice.rubric == "sentiment-jev@1"


def test_the_environment_can_move_the_jev_provider_to_another_rubric(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "sentiment-jev"
    directory.mkdir()
    source = (PROMPTS / "sentiment-jev" / "v1.yaml").read_text(encoding="utf-8")
    (directory / "v2.yaml").write_text(
        source.replace("version: 1", "version: 2"), encoding="utf-8"
    )

    choice = build(
        "jev",
        jev_api_key=SecretStr("jev"),
        sentiment_rubric="sentiment-jev@2",
        prompts_dir=tmp_path,
    )

    assert choice.model == "jev-1.13.0"
    assert choice.rubric == "sentiment-jev@2"


def test_an_unknown_provider_is_refused() -> None:
    with pytest.raises(SentimentSetupError, match="unknown"):
        build("magic")


async def test_both_classifiers_audit_a_fallback_the_same_way() -> None:
    """The port conformance test: same event names, same fields, same keyword signal."""
    expected = await KeywordSentiment().classify(TEXT, source="survey:manager")
    prompt_audit = RecordingAudit()
    prompt = SentimentClassifier(
        llm=ScriptedLLM(responses=[LLMUnavailableError("down")]),
        prompts=PromptLibrary(PROMPTS),
        audit=prompt_audit,
    )
    jev_client = client(lambda _: httpx.Response(503, json={}))
    jev_audit = RecordingAudit()
    jev = build("jev", audit=jev_audit, jev_api_key=SecretStr("jev"), http=jev_client)

    prompt_signal = await prompt.classify(TEXT, source="survey:manager")
    jev_signal = await jev.classifier.classify(TEXT, source="survey:manager")

    assert prompt_audit.names() == jev_audit.names() == ["sentiment_fallback"]
    for audit in (prompt_audit, jev_audit):
        fields = audit.events[0][1]
        assert fields["source"] == "survey:manager"
        assert "provider" in fields
        assert "reason" in fields
    _assert_same_signal(prompt_signal, expected)
    _assert_same_signal(jev_signal, expected)


async def test_both_classifiers_audit_a_format_error_the_same_way() -> None:
    prompt_audit = RecordingAudit()
    prompt = SentimentClassifier(
        llm=ScriptedLLM(responses=["не JSON вовсе"]),
        prompts=PromptLibrary(PROMPTS),
        audit=prompt_audit,
    )
    jev_client = client(lambda _: httpx.Response(200, json=jev_answers("angry")))
    jev_audit = RecordingAudit()
    jev = build("jev", audit=jev_audit, jev_api_key=SecretStr("jev"), http=jev_client)

    await prompt.classify(TEXT, source="survey:manager")
    await jev.classifier.classify(TEXT, source="survey:manager")

    assert prompt_audit.names() == ["sentiment_fallback"]
    assert jev_audit.names() == ["sentiment_format_error", "sentiment_fallback"]


async def test_the_jev_classifier_measures_what_it_spent() -> None:
    audit = RecordingAudit()
    body = jev_answers()
    body["usage"] = {"input_tokens": 500}
    choice = build(
        "jev",
        audit=audit,
        jev_api_key=SecretStr("jev"),
        jev_price_input_rub_per_1k=0.4,
        http=client(lambda _: httpx.Response(200, json=body)),
    )

    await choice.classifier.classify(TEXT, source="survey:manager")

    _, fields = audit.events[0]
    assert fields["input_tokens"] == 500
    assert fields["cost_rub"] == pytest.approx(0.2)
    assert fields["rubric"] == "sentiment-jev@1"
    assert fields["model"] == "jev-1.13.0"
    assert isinstance(fields["latency_ms"], int)


def test_the_code_limit_matches_the_sentiment_contract() -> None:
    schema = json.loads((CONTRACTS / "sentiment.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["tags"]["maxItems"] == MAX_TAGS


def test_the_shipped_rubric_fits_the_code_limit() -> None:
    rubric = yaml.safe_load(
        (PROMPTS / "sentiment-jev" / "v1.yaml").read_text(encoding="utf-8")
    )

    assert rubric["max_tags"] <= MAX_TAGS


def _assert_same_signal(actual: RiskSignal, expected: RiskSignal) -> None:
    assert actual.sentiment is expected.sentiment
    assert actual.tags == expected.tags
    assert actual.source == expected.source
    assert actual.text == expected.text


async def test_the_prompt_classifier_reports_the_same_usage_fields_as_jev() -> None:
    """One Cost section prices either path, so both audit events carry tokens and latency."""
    audit = RecordingAudit()
    classifier = SentimentClassifier(
        llm=ScriptedLLM(
            responses=[
                '{"sentiment": "negative", "tags": ["access"], "confidence": 0.9, "reason": "x"}'
            ]
        ),
        prompts=PromptLibrary(PROMPTS),
        audit=audit,
    )

    await classifier.classify("Доступ не выдали третий день", source="day_three")

    name, fields = audit.events[0]
    assert name == "sentiment_classified"
    assert fields["provider"] == "prompt"
    assert fields["input_tokens"] == 10
    assert fields["output_tokens"] == 5
    assert fields["model"] == "scripted"
    assert "latency_ms" in fields
