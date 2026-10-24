"""The sentiment layer: two model classifiers, one deterministic fallback, one way to build them.

The prompt classifier labels one answer with the versioned chat prompt; the Jev classifier labels
it with a rubric and returns probabilities. Both satisfy :class:`SentimentAnalysis`, both degrade
to ``core/risk.keyword_signal`` through :mod:`onboarding.app.llm.fallback`, and both are built by
:func:`build_sentiment`, so the composition root and the eval runner cannot choose differently.

Parsing here is strict for the same reason as ``output.py``: model output is untrusted, and a
malformed label must degrade to the keyword fallback, not to a silent guess.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from onboarding.app.audit import NullAudit
from onboarding.app.llm.fallback import (
    MAX_ANSWER_CHARS,
    MAX_TAGS,
    TAGS,
    KeywordSentiment,
    fallback_signal,
)
from onboarding.app.llm.gateway import LLMResponseError
from onboarding.app.llm.jev import build_jev_classifier
from onboarding.app.llm.output import AnswerFormatError, parse_json_object
from onboarding.app.llm.profiles import classify_profile
from onboarding.app.llm.rubric import RubricLibrary
from onboarding.app.llm.transport import model_breaker
from onboarding.app.prompts import PromptLibrary
from onboarding.app.settings import Settings
from onboarding.core.models import RiskSignal, Sentiment, SignalTag
from onboarding.ports import (
    LLM,
    AuditLog,
    ClassifyProfile,
    Clock,
    CompletionRequest,
    LLMUnavailableError,
    Message,
    SentimentAnalysis,
)

PROMPT_NAME = "sentiment"
PROMPT_VERSION = 1
MAX_REASON_CHARS = 200

__all__ = [
    "MAX_ANSWER_CHARS",
    "MAX_TAGS",
    "PROMPT_NAME",
    "PROMPT_VERSION",
    "KeywordSentiment",
    "SentimentClassifier",
    "SentimentFormatError",
    "SentimentSetupError",
    "build_sentiment",
    "parse_sentiment",
]


class SentimentFormatError(AnswerFormatError):
    """The model did not honour the sentiment contract."""


class SentimentSetupError(ValueError):
    """The selected provider cannot run: a missing key, or an unbuildable model profile."""


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
        tag = TAGS.get(str(item))
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


class SentimentClassifier:
    """Label one free-text answer, with the keyword classifier as the safety net.

    The model call is optional by design: an outage lowers precision, never availability. Every
    fallback is audited, so a "calm" week is distinguishable from a broken classifier.
    """

    def __init__(
        self,
        *,
        llm: LLM,
        prompts: PromptLibrary,
        audit: AuditLog | None = None,
        timeout_s: float = 8.0,
        max_tokens: int = 300,
    ) -> None:
        self._llm = llm
        self._prompts = prompts
        self._audit = audit or NullAudit()
        self._timeout = timeout_s
        self._max_tokens = max_tokens

    async def classify(self, text: str, *, source: str) -> RiskSignal:
        prompt = self._prompts.load(PROMPT_NAME, PROMPT_VERSION)
        rendered = prompt.render({"answer": text[:MAX_ANSWER_CHARS]})
        try:
            completion = await self._llm.complete(
                CompletionRequest(
                    messages=(Message(role="system", content=rendered),),
                    temperature=prompt.temperature,
                    max_tokens=self._max_tokens,
                    prompt_name=PROMPT_NAME,
                    prompt_version=PROMPT_VERSION,
                    timeout_s=self._timeout,
                )
            )
        except (LLMUnavailableError, LLMResponseError):
            return await self._fallback(text, source, reason="unavailable")
        try:
            draft = parse_sentiment(completion.text)
        except AnswerFormatError:
            return await self._fallback(text, source, reason="format")
        await self._audit.record(
            "sentiment_classified",
            source=source,
            provider="prompt",
            model=completion.model,
            sentiment=draft.sentiment.value,
            tags=[tag.value for tag in draft.tags],
            confidence=draft.confidence,
            prompt_version=PROMPT_VERSION,
            # The same fields the Jev adapter records, so one Cost section prices either path.
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
            latency_ms=completion.latency_ms,
            cost_rub=completion.cost_rub,
        )
        return RiskSignal(
            source=source,
            sentiment=draft.sentiment,
            tags=draft.tags,
            confidence=draft.confidence,
            text=text,
        )

    async def _fallback(self, text: str, source: str, *, reason: str) -> RiskSignal:
        return await fallback_signal(
            self._audit, text, source, provider="prompt", reason=reason
        )


@dataclass(frozen=True, slots=True)
class SentimentChoice:
    """What was built, and what it is: a measurement must name the model and the rubric."""

    provider: str
    classifier: SentimentAnalysis
    model: str = ""
    rubric: str = ""
    prompt_version: int | None = None


def build_sentiment(
    settings: Settings,
    *,
    clock: Clock,
    client: httpx.AsyncClient,
    prompts: PromptLibrary,
    audit: AuditLog | None = None,
    llm: LLM | None = None,
    provider: str | None = None,
) -> SentimentChoice:
    """Build the configured classifier. The only place that knows a provider or a rubric path."""
    chosen = provider or settings.sentiment_provider
    if chosen == "keyword":
        return SentimentChoice(provider="keyword", classifier=KeywordSentiment())
    if chosen == "prompt":
        if llm is None or not settings.is_llm_configured:
            raise SentimentSetupError("LLM_API_KEY is not set; the prompt provider cannot run")
        return SentimentChoice(
            provider="prompt",
            classifier=SentimentClassifier(llm=llm, prompts=prompts, audit=audit),
            model=settings.llm_profile,
            prompt_version=PROMPT_VERSION,
        )
    if chosen == "jev":
        if not settings.jev_api_key.get_secret_value():
            raise SentimentSetupError("JEV_API_KEY is not set; the jev provider cannot run")
        profile = _classify_profile(settings)
        classifier = build_jev_classifier(
            client=client,
            endpoint=f"{settings.jev_base_url.rstrip('/')}/systemone",
            api_key=settings.jev_api_key,
            profile=profile,
            rubrics=RubricLibrary(
                settings.prompts_dir, settings.contracts_dir / "jev-rubric.schema.json"
            ),
            audit=audit,
            clock=clock,
            breaker=model_breaker(settings),
        )
        return SentimentChoice(
            provider="jev",
            classifier=classifier,
            model=profile.model,
            rubric=profile.rubric,
        )
    raise SentimentSetupError(f"unknown sentiment provider {chosen!r}")


def _classify_profile(settings: Settings) -> ClassifyProfile:
    try:
        return classify_profile(settings)
    except ValueError as error:
        raise SentimentSetupError(str(error)) from None
