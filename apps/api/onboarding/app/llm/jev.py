"""TypeSafe Jev as an alternative sentiment classifier.

Jev is not a chat model: it takes one ``state`` and a map of typed questions and returns
probabilities. The rubric in ``docs/prompts/sentiment-jev/v1.yaml`` is therefore the prompt, and
this module only transports and validates. A malformed answer degrades to the keyword classifier,
exactly like a broken chat completion does in ``sentiment.py``.
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import yaml
from pydantic import SecretStr

from onboarding.app.audit import NullAudit
from onboarding.core.models import RiskSignal, Sentiment, SignalTag
from onboarding.core.risk import keyword_signal
from onboarding.ports import AuditLog, SentimentAnalysis

RUBRIC_NAME = "sentiment-jev"
RUBRIC_VERSION = 1
MAX_ANSWER_CHARS = 2000
MAX_TAGS = 3
_PROBABILITY_TOLERANCE = 0.05
_TAGS = {tag.value: tag for tag in SignalTag}


class JevError(RuntimeError):
    """Base class for anything that makes the Jev verdict unusable."""


class JevUnavailableError(JevError):
    """The endpoint did not answer, or answered with a non-retryable error."""


class JevFormatError(JevError):
    """The endpoint answered, but not inside the contract."""


@dataclass(frozen=True, slots=True)
class JevQuestion:
    type: str
    instructions: str
    criteria: tuple[str, ...] = ()

    def payload(self) -> dict[str, Any]:
        body: dict[str, Any] = {"type": self.type, "instructions": self.instructions}
        if self.criteria:
            body["criteria"] = list(self.criteria)
        return body


@dataclass(frozen=True, slots=True)
class JevRubric:
    version: int
    model: str
    tag_threshold: float
    max_tags: int
    questions: dict[str, JevQuestion]

    @property
    def sentiment_criteria(self) -> tuple[str, ...]:
        return self.questions["sentiment"].criteria


@dataclass(frozen=True, slots=True)
class JevVerdict:
    sentiment: Sentiment
    tags: tuple[SignalTag, ...]
    confidence: float
    probabilities: dict[str, float]


def load_rubric(path: Path) -> JevRubric:
    """Read the versioned rubric and refuse to run on a shape this module cannot map."""
    payload = _read_rubric(path)
    model, threshold, max_tags = _header(payload, path)
    questions = _questions(payload.get("questions"), path)
    sentiment = questions.get("sentiment")
    if sentiment is None or sentiment.type != "choice":
        raise JevFormatError(f"{path}: a choice question named 'sentiment' is required")
    if set(sentiment.criteria) != {item.value for item in Sentiment}:
        raise JevFormatError(f"{path}: sentiment criteria must match the Sentiment enum")
    if not any(key.startswith("tag_") for key in questions):
        raise JevFormatError(f"{path}: at least one tag question is required")
    return JevRubric(
        version=RUBRIC_VERSION,
        model=model,
        tag_threshold=threshold,
        max_tags=max_tags,
        questions=questions,
    )


def _read_rubric(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise JevFormatError(f"missing rubric {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise JevFormatError(f"{path}: rubric must be a mapping")
    return payload


def _header(payload: dict[str, Any], path: Path) -> tuple[str, float, int]:
    if payload.get("name") != RUBRIC_NAME:
        raise JevFormatError(f"{path}: name must be {RUBRIC_NAME!r}")
    if payload.get("version") != RUBRIC_VERSION:
        raise JevFormatError(f"{path}: version must be {RUBRIC_VERSION}")
    model = payload.get("model")
    if not isinstance(model, str) or not model:
        raise JevFormatError(f"{path}: model must be a non-empty string")
    threshold = _unit_interval(payload.get("tag_threshold"), f"{path}: tag_threshold")
    max_tags = payload.get("max_tags")
    if not isinstance(max_tags, int) or isinstance(max_tags, bool) or not 1 <= max_tags <= MAX_TAGS:
        raise JevFormatError(f"{path}: max_tags must be within [1, {MAX_TAGS}]")
    return model, threshold, max_tags


def _questions(raw: Any, path: Path) -> dict[str, JevQuestion]:
    if not isinstance(raw, dict) or not raw:
        raise JevFormatError(f"{path}: questions must be a non-empty mapping")
    questions: dict[str, JevQuestion] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            raise JevFormatError(f"{path}: questions must map names to mappings")
        questions[key] = _question(key, value, path)
    return questions


def _question(key: str, value: dict[str, Any], path: Path) -> JevQuestion:
    question_type = value.get("type")
    instructions = value.get("instructions")
    if question_type not in {"noul", "choice"}:
        raise JevFormatError(f"{path}: {key}: unsupported type {question_type!r}")
    if not isinstance(instructions, str) or not instructions.strip():
        raise JevFormatError(f"{path}: {key}: instructions must be a non-empty string")
    criteria = value.get("criteria") or []
    if not isinstance(criteria, list) or not all(isinstance(item, str) for item in criteria):
        raise JevFormatError(f"{path}: {key}: criteria must be a list of strings")
    if question_type == "choice" and len(criteria) < 2:
        raise JevFormatError(f"{path}: {key}: a choice needs at least two options")
    if question_type == "noul" and criteria:
        raise JevFormatError(f"{path}: {key}: a noul question takes no criteria list")
    if key.startswith("tag_") and key.removeprefix("tag_") not in _TAGS:
        raise JevFormatError(f"{path}: {key}: unknown signal tag")
    return JevQuestion(
        type=str(question_type),
        instructions=instructions.strip(),
        criteria=tuple(criteria),
    )


def parse_jev(payload: Any, rubric: JevRubric) -> JevVerdict:
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
    for key, question in rubric.questions.items():
        if question.type != "noul" or not key.startswith("tag_"):
            continue
        probability = _noul(answers.get(key), key)
        scored.append((probability, _TAGS[key.removeprefix("tag_")]))
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
        rubric: JevRubric,
        audit: AuditLog | None = None,
        timeout_s: float = 8.0,
        max_retries: int = 2,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must not be negative")
        self._client = client
        self._endpoint = endpoint
        self._api_key = api_key
        self._rubric = rubric
        self._audit = audit or NullAudit()
        self._timeout = timeout_s
        self._max_retries = max_retries

    async def classify(self, text: str, *, source: str) -> RiskSignal:
        state = text[:MAX_ANSWER_CHARS]
        try:
            payload = await self._ask(state)
            verdict = parse_jev(payload, self._rubric)
        except JevUnavailableError:
            return await self._fallback(text, source, reason="jev_unavailable")
        except JevFormatError as error:
            await self._audit.record(
                "sentiment_format_error", source=source, provider="jev", error=str(error)
            )
            return await self._fallback(text, source, reason="jev_format")
        await self._audit.record(
            "sentiment_classified",
            source=source,
            provider="jev",
            model=self._rubric.model,
            rubric_version=self._rubric.version,
            sentiment=verdict.sentiment.value,
            tags=[tag.value for tag in verdict.tags],
            confidence=verdict.confidence,
            probabilities=verdict.probabilities,
        )
        return RiskSignal(
            source=source,
            sentiment=verdict.sentiment,
            tags=verdict.tags,
            confidence=verdict.confidence,
            text=text,
        )

    async def _ask(self, state: str) -> Any:
        body = {
            "model": self._rubric.model,
            "state": state,
            "questions": {key: value.payload() for key, value in self._rubric.questions.items()},
        }
        headers = {
            "Authorization": f"Bearer {self._api_key.get_secret_value()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        last = "no attempt"
        for attempt in range(self._max_retries + 1):
            if attempt:
                await asyncio.sleep(0.2 * attempt)
            try:
                response = await self._client.post(
                    self._endpoint, headers=headers, json=body, timeout=self._timeout
                )
            except httpx.HTTPError as error:
                last = f"jev request failed: {error}"
                continue
            if response.status_code in {429, 500, 502, 503, 504} and attempt < self._max_retries:
                last = f"jev endpoint answered {response.status_code}"
                continue
            if response.status_code >= 400:
                raise JevUnavailableError(f"jev endpoint answered {response.status_code}")
            try:
                return response.json()
            except ValueError as error:
                raise JevFormatError(f"jev response is not JSON: {error}") from None
        raise JevUnavailableError(last)

    async def _fallback(self, text: str, source: str, *, reason: str) -> RiskSignal:
        await self._audit.record(
            "sentiment_fallback", source=source, provider="jev", reason=reason
        )
        return keyword_signal(text, source=source)


def build_jev_classifier(
    *,
    client: httpx.AsyncClient,
    endpoint: str,
    api_key: SecretStr,
    rubric_path: Path,
    audit: AuditLog | None = None,
    timeout_s: float = 8.0,
    max_retries: int = 2,
) -> SentimentAnalysis:
    return JevSentimentClassifier(
        client=client,
        endpoint=endpoint,
        api_key=api_key,
        rubric=load_rubric(rubric_path),
        audit=audit,
        timeout_s=timeout_s,
        max_retries=max_retries,
    )
