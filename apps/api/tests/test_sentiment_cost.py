"""The eval reports the price the classifier measured, not a price someone remembered."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import httpx
from pydantic import SecretStr

from onboarding.app.clock import FrozenClock
from onboarding.app.llm.rubric import RubricLibrary
from onboarding.app.llm.sentiment import SentimentChoice, build_sentiment
from onboarding.app.prompts import PromptLibrary
from onboarding.app.settings import REPO_ROOT, Settings
from onboarding.core.models import Sentiment
from onboarding.evals.sentiment import (
    Case,
    CountingAudit,
    evaluate,
    load_artifact,
    render_artifact,
    render_markdown,
)

from .conftest import NOW

PROMPTS = REPO_ROOT / "docs" / "prompts"
CONTRACTS = REPO_ROOT / "docs" / "contracts"
CASES = (
    Case(id="case-1", text="Доступ не выдали, третий день", sentiment=Sentiment.NEGATIVE, tags=()),
)


def answers(tokens: int) -> dict[str, object]:
    rubric = RubricLibrary(PROMPTS, CONTRACTS / "jev-rubric.schema.json").load(
        "sentiment-jev@1"
    )
    return {
        "usage": {"input_tokens": tokens},
        "answers": {
            "sentiment": {
                "type": "choice",
                "choice": "negative",
                "probabilities": {
                    "positive": 0.05,
                    "neutral": 0.15,
                    "negative": 0.8,
                    "unknown": 0.0,
                },
            },
            **{key: {"type": "noul", "noul": 0.9} for key in rubric.tags},
        },
    }


def choice_for(
    handler: Callable[[httpx.Request], httpx.Response], audit: CountingAudit
) -> SentimentChoice:
    settings = Settings(
        _env_file=None,
        sentiment_provider="jev",
        classify_profile="jev-1.13.0",
        jev_api_key=SecretStr("jev"),
        jev_price_input_rub_per_1k=0.5,
    )
    return build_sentiment(
        settings,
        clock=FrozenClock(NOW),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        prompts=PromptLibrary(PROMPTS),
        audit=audit,
        provider="jev",
    )


async def test_a_run_reports_its_measured_spend() -> None:
    audit = CountingAudit()
    choice = choice_for(lambda _: httpx.Response(200, json=answers(200)), audit)

    report = await evaluate(
        CASES,
        choice.classifier,
        provider="jev",
        audit=audit,
        identity=choice,
    )

    assert report.input_tokens == 200
    assert report.cost_rub == 0.1
    assert report.cost_per_1k_calls == 100.0
    assert "## Cost" in render_markdown(report, command="cmd", note="")


async def test_the_artifact_keeps_the_price_and_the_identity(tmp_path: Path) -> None:
    audit = CountingAudit()
    choice = choice_for(lambda _: httpx.Response(200, json=answers(1000)), audit)
    report = await evaluate(
        CASES,
        choice.classifier,
        provider="jev",
        audit=audit,
        identity=choice,
    )

    path = tmp_path / "run.jsonl"
    path.write_text(render_artifact(report, command="cmd"), encoding="utf-8")
    restored = load_artifact(path)

    assert restored.model == "jev-1.13.0"
    assert restored.rubric == "sentiment-jev@1"
    assert restored.input_tokens == 1000
    assert restored.cost_rub == 0.5
