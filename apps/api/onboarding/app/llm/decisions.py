"""A decisions model as the sentiment classifier: one state, typed questions, probabilities.

A decisions model is not a chat model. It reads one ``state`` once and answers a map of typed
questions, so the rubric in ``docs/prompts/sentiment-jev/`` is the prompt and this module only
transports and validates. Nothing here knows a vendor: the endpoint, model, rubric, envelope, and
price come from a ``classify`` profile (``apps/api/model-profiles/classify/<name>.yaml``), so a
second decisions model is a new profile plus an eval run, not a branch in the composition root.
The shipped profiles point at TypeSafe Jev, which speaks the System One wire shape below.

A malformed answer degrades to the keyword classifier, exactly like a broken chat completion does
in ``sentiment.py``.
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
from onboarding.app.llm.usage import reported_cost_usd
from onboarding.core.breaker import CircuitBreaker
from onboarding.core.models import RiskSignal, Sentiment, SignalTag
from onboarding.ports import AuditLog, ClassifyProfile, Clock, SentimentAnalysis

_PROBABILITY_TOLERANCE = 0.05


class DecisionsError(RuntimeError):
    """Base class for anything that makes the decisions verdict unusable."""


class DecisionsUnavailableError(DecisionsError):
    """The endpoint did not answer, or answered with a non-retryable error."""


class DecisionsFormatError(DecisionsError):
    """The endpoint answered, but not inside the contract."""


@dataclass(frozen=True, slots=True)
class DecisionsVerdict:
    sentiment: Sentiment
    tags: tuple[SignalTag, ...]
    confidence: float
    probabilities: dict[str, float]


def parse_decisions(payload: Any, rubric: Rubric) -> DecisionsVerdict:
    """Validate one response against the rubric. Extra answers are ignored, missing ones fail."""
    if not isinstance(payload, dict):
        raise DecisionsFormatError("response must be an object")
    answers = payload.get("answers")
    if not isinstance(answers, dict):
        raise DecisionsFormatError("response has no answers object")

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

    return DecisionsVerdict(
        sentiment=sentiment,
        tags=tags,
        confidence=confidence,
        probabilities=probabilities,
    )


def _choice(value: Any, criteria: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("type") != "choice":
        raise DecisionsFormatError("sentiment answer must be a choice")
    choice = value.get("choice")
    if not isinstance(choice, str) or choice not in criteria:
        raise DecisionsFormatError(f"unknown choice {choice!r}")
    raw = value.get("probabilities")
    if not isinstance(raw, dict) or set(raw) != set(criteria):
        raise DecisionsFormatError("sentiment probabilities must cover every option")
    probabilities = {
        key: _unit_interval(probability, f"probability {key!r}")
        for key, probability in raw.items()
    }
    if abs(sum(probabilities.values()) - 1.0) > _PROBABILITY_TOLERANCE:
        raise DecisionsFormatError("sentiment probabilities must sum to 1")
    if probabilities[choice] < max(probabilities.values()) - _PROBABILITY_TOLERANCE:
        raise DecisionsFormatError("the chosen sentiment is not the most probable one")
    return {"choice": choice, "probabilities": probabilities, "confidence": value.get("confidence")}


def _noul(value: Any, key: str) -> float:
    if not isinstance(value, dict) or value.get("type") != "noul":
        raise DecisionsFormatError(f"{key}: answer must be noul")
    return _unit_interval(value.get("noul"), f"{key}.noul")


def _confidence(raw: Any, probabilities: dict[str, float]) -> float:
    if raw is None:
        return max(probabilities.values())
    return _unit_interval(raw, "confidence")


def _unit_interval(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise DecisionsFormatError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise DecisionsFormatError(f"{label} must be within [0, 1]")
    return number


class DecisionsClassifier:
    """Label one free-text answer with a decisions model, the keyword classifier as the net."""

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
            verdict = parse_decisions(payload, self._rubric)
        except DecisionsUnavailableError as error:
            return await self._fallback(
                text, source, reason="decisions_unavailable", detail=str(error)
            )
        except DecisionsFormatError as error:
            await self._audit.record(
                "sentiment_format_error", source=source, provider="decisions", error=str(error)
            )
            return await self._fallback(text, source, reason="decisions_format")
        input_tokens = _input_tokens(payload)
        cost_usd = reported_cost_usd(payload.get("usage") if isinstance(payload, dict) else None)
        await self._audit.record(
            "sentiment_classified",
            source=source,
            provider="decisions",
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
            # The provider's own number, when it sends one (OpenRouter does). A price we did not
            # measure is a guess; this is the ledger.
            cost_usd=None if cost_usd is None else round(cost_usd, 9),
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
                prepare=lambda: self._prepare(headers, self._body(state)),
                timeout_s=self._profile.timeout_s,
                max_retries=self._profile.max_retries,
                parse=self._parse,
            )
        except RejectedError as error:
            raise DecisionsUnavailableError(
                f"decisions endpoint answered {error.status_code}"
            ) from None
        except TransportError as error:
            raise DecisionsUnavailableError(f"decisions request failed: {error}") from None
        return payload, elapsed_s

    async def _prepare(
        self, headers: dict[str, str], body: dict[str, object]
    ) -> PreparedRequest:
        return PreparedRequest(url=self._endpoint, headers=headers, body=body)

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
            raise DecisionsFormatError(f"decisions response is not JSON: {error}") from None
        if not isinstance(payload, dict):
            raise DecisionsFormatError("response must be an object")
        _refuse_an_error_envelope(payload)
        return payload, elapsed_s

    async def _fallback(
        self, text: str, source: str, *, reason: str, detail: str = ""
    ) -> RiskSignal:
        return await fallback_signal(
            self._audit, text, source, provider="decisions", reason=reason, error=detail
        )


def _refuse_an_error_envelope(payload: dict[str, Any]) -> None:
    """A 200 with ``success: false`` is an outage with a reason, not a malformed answer.

    OpenRouter answers a blocked key or a policy denial this way. Reading it as a format error
    would send an operator to the rubric for something only the provider account can fix.
    """
    if payload.get("success") is not False and "answers" in payload:
        return
    error = payload.get("error")
    detail = error if isinstance(error, str) else "no reason given"
    raise DecisionsUnavailableError(f"decisions endpoint refused the call: {detail[:200]}")


def _input_tokens(payload: Any) -> int:
    usage = payload.get("usage") if isinstance(payload, dict) else None
    tokens = usage.get("input_tokens") if isinstance(usage, dict) else None
    return tokens if isinstance(tokens, int) and not isinstance(tokens, bool) else 0


def build_decisions_classifier(
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
    return DecisionsClassifier(
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
