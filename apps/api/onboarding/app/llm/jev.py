"""TypeSafe Jev as an alternative sentiment classifier.

Jev is not a chat model: it takes one ``state`` and a map of typed questions and returns
probabilities. The rubric in ``docs/prompts/sentiment-jev/`` is therefore the prompt, and this
module only transports and validates. A malformed answer degrades to the keyword classifier,
exactly like a broken chat completion does in ``sentiment.py``.

The model, envelope, rubric, and price come from a ``classify`` profile
(``apps/api/model-profiles/classify/<name>.yaml``), so a new classifier is a file plus an eval run,
not a branch in the composition root.
"""

from __future__ import annotations

import asyncio
import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import SecretStr

from onboarding.app.audit import NullAudit
from onboarding.app.clock import SystemClock
from onboarding.app.llm.fallback import MAX_ANSWER_CHARS, fallback_signal
from onboarding.app.llm.providers import PreparedRequest
from onboarding.app.llm.rubric import Rubric, RubricLibrary
from onboarding.app.llm.transport import ModelTransport, RejectedError, TransportError
from onboarding.core.breaker import CircuitBreaker
from onboarding.core.models import RiskSignal, Sentiment, SignalTag
from onboarding.ports import AuditLog, ClassifyProfile, Clock, SentimentAnalysis

_PROBABILITY_TOLERANCE = 0.05


class JevError(RuntimeError):
    """Base class for anything that makes the Jev verdict unusable."""


class JevUnavailableError(JevError):
    """The endpoint did not answer, or answered with a non-retryable error."""


class JevFormatError(JevError):
    """The endpoint answered, but not inside the contract."""


@dataclass(frozen=True, slots=True)
class JevVerdict:
    sentiment: Sentiment
    tags: tuple[SignalTag, ...]
    confidence: float
    probabilities: dict[str, float]


def parse_jev(payload: Any, rubric: Rubric) -> JevVerdict:
    """Validate one response against the rubric. Extra answers are ignored, missing ones fail."""
    if not isinstance(payload, dict):
        raise JevFormatError("response must be an object")
    answers = payload.get("answers")
    if not isinstance(answers, dict):
        raise JevFormatError("response has no answers object")

    choice = _choice(answers.get("sentiment"), rubric.sentiment_criteria)
    sentiment = Sentiment(choice["choice"])
    probabilities = choice["probabilities"]
    confidence = _confidence(choice.get("confidence"), probabilities)

    scored: list[tuple[float, SignalTag]] = []
    for key, tag in rubric.tags.items():
        probability = _noul(answers.get(key), key)
        scored.append((probability, tag))
    scored.sort(key=lambda item: (-item[0], item[1].value))
    tags = tuple(tag for probability, tag in scored if probability >= rubric.tag_threshold)[
        : rubric.max_tags
    ]
    if not tags and scored:
        tags = (scored[0][1],)

    return JevVerdict(
        sentiment=sentiment,
        tags=tags,
        confidence=confidence,
        probabilities=probabilities,
    )


def _choice(value: Any, criteria: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("type") != "choice":
        raise JevFormatError("sentiment answer must be a choice")
    choice = value.get("choice")
    if not isinstance(choice, str) or choice not in criteria:
        raise JevFormatError(f"unknown choice {choice!r}")
    raw = value.get("probabilities")
    if not isinstance(raw, dict) or set(raw) != set(criteria):
        raise JevFormatError("sentiment probabilities must cover every option")
    probabilities = {
        key: _unit_interval(probability, f"probability {key!r}")
        for key, probability in raw.items()
    }
    if abs(sum(probabilities.values()) - 1.0) > _PROBABILITY_TOLERANCE:
        raise JevFormatError("sentiment probabilities must sum to 1")
    if probabilities[choice] < max(probabilities.values()) - _PROBABILITY_TOLERANCE:
        raise JevFormatError("the chosen sentiment is not the most probable one")
    return {"choice": choice, "probabilities": probabilities, "confidence": value.get("confidence")}


def _noul(value: Any, key: str) -> float:
    if not isinstance(value, dict) or value.get("type") != "noul":
        raise JevFormatError(f"{key}: answer must be noul")
    return _unit_interval(value.get("noul"), f"{key}.noul")


def _confidence(raw: Any, probabilities: dict[str, float]) -> float:
    if raw is None:
        return max(probabilities.values())
    return _unit_interval(raw, "confidence")


def _unit_interval(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise JevFormatError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise JevFormatError(f"{label} must be within [0, 1]")
    return number


class JevSentimentClassifier:
    """Label one free-text answer with Jev, keeping the keyword classifier as the safety net."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        endpoint: str,
        api_key: SecretStr,
        profile: ClassifyProfile,
        rubric: Rubric,
        audit: AuditLog | None = None,
        clock: Clock | None = None,
        breaker: CircuitBreaker | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._endpoint = endpoint
        self._api_key = api_key
        self._profile = profile
        self._rubric = rubric
        self._audit = audit or NullAudit()
        self._transport = ModelTransport(
            client=client,
            clock=clock or SystemClock(),
            breaker=breaker or CircuitBreaker(),
            sleep=sleep,
        )

    @property
    def profile(self) -> ClassifyProfile:
        return self._profile

    @property
    def rubric(self) -> Rubric:
        return self._rubric

    @property
    def breaker(self) -> CircuitBreaker:
        return self._transport.breaker

    async def classify(self, text: str, *, source: str) -> RiskSignal:
        state = text[:MAX_ANSWER_CHARS]
        try:
            payload, elapsed_s = await self._ask(state)
            verdict = parse_jev(payload, self._rubric)
        except JevUnavailableError:
            return await self._fallback(text, source, reason="jev_unavailable")
        except JevFormatError as error:
            await self._audit.record(
                "sentiment_format_error", source=source, provider="jev", error=str(error)
            )
            return await self._fallback(text, source, reason="jev_format")
        input_tokens = _input_tokens(payload)
        await self._audit.record(
            "sentiment_classified",
            source=source,
            provider="jev",
            model=self._profile.model,
            rubric=self._rubric.selector,
            rubric_version=self._rubric.version,
            sentiment=verdict.sentiment.value,
            tags=[tag.value for tag in verdict.tags],
            confidence=verdict.confidence,
            probabilities=verdict.probabilities,
            input_tokens=input_tokens,
            latency_ms=int(elapsed_s * 1000),
            cost_rub=round(input_tokens / 1000 * self._profile.price_input_rub_per_1k, 6),
        )
        return RiskSignal(
            source=source,
            sentiment=verdict.sentiment,
            tags=verdict.tags,
            confidence=verdict.confidence,
            text=text,
        )

    async def _ask(self, state: str) -> tuple[Any, float]:
        headers = {
            "Authorization": f"Bearer {self._api_key.get_secret_value()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            payload, elapsed_s = await self._transport.call(
                prepare=lambda: self._prepare(headers),
                payload=self._body(state),
                timeout_s=self._profile.timeout_s,
                max_retries=self._profile.max_retries,
                parse=self._parse,
            )
        except RejectedError as error:
            raise JevUnavailableError(f"jev endpoint answered {error.status_code}") from None
        except TransportError as error:
            raise JevUnavailableError(f"jev request failed: {error}") from None
        return payload, elapsed_s

    async def _prepare(self, headers: dict[str, str]) -> PreparedRequest:
        return PreparedRequest(url=self._endpoint, headers=headers)

    def _body(self, state: str) -> dict[str, object]:
        return {
            "model": self._profile.model,
            "state": state,
            "questions": {key: value.payload() for key, value in self._rubric.questions.items()},
        }

    def _parse(self, response: httpx.Response, elapsed_s: float) -> tuple[Any, float]:
        try:
            payload: Any = response.json()
        except ValueError as error:
            raise JevFormatError(f"jev response is not JSON: {error}") from None
        if not isinstance(payload, dict):
            raise JevFormatError("response must be an object")
        return payload, elapsed_s

    async def _fallback(self, text: str, source: str, *, reason: str) -> RiskSignal:
        return await fallback_signal(
            self._audit, text, source, provider="jev", reason=reason
        )


def _input_tokens(payload: Any) -> int:
    usage = payload.get("usage") if isinstance(payload, dict) else None
    tokens = usage.get("input_tokens") if isinstance(usage, dict) else None
    return tokens if isinstance(tokens, int) and not isinstance(tokens, bool) else 0


def build_jev_classifier(
    *,
    client: httpx.AsyncClient,
    endpoint: str,
    api_key: SecretStr,
    profile: ClassifyProfile,
    rubrics: RubricLibrary,
    audit: AuditLog | None = None,
    clock: Clock | None = None,
    breaker: CircuitBreaker | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> SentimentAnalysis:
    return JevSentimentClassifier(
        client=client,
        endpoint=endpoint,
        api_key=api_key,
        profile=profile,
        rubric=rubrics.load(profile.rubric),
        audit=audit,
        clock=clock,
        breaker=breaker,
        sleep=sleep,
    )
