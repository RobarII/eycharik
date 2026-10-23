"""Strict parsing of model output.

The model is a text generator, so its output is untrusted input. Parsing is defensive, bounded, and
fails with a typed error instead of a ``KeyError`` deep inside the worker.
"""

from __future__ import annotations

import json
import re
from typing import Any

from onboarding.core.models import AnswerDraft, ChunkId

MAX_OUTPUT_CHARS = 20_000
_CITATION = re.compile(r"^[a-z0-9][a-z0-9/_-]*#[0-9]+$")
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_TRAILING_COMMA = re.compile(r",\s*([}\]])")
_ALLOWED_REASONS = {"answered", "no_sources", "low_confidence", "restricted", "out_of_scope"}


class AnswerFormatError(ValueError):
    """The model did not honour the answer contract."""


def parse_json_object(text: str) -> dict[str, Any]:
    if len(text) > MAX_OUTPUT_CHARS:
        raise AnswerFormatError("model output is unreasonably long")
    candidate = _FENCE.sub("", text).strip()
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end <= start:
        raise AnswerFormatError("no JSON object in model output")
    payload = candidate[start : end + 1]
    for attempt in (payload, _TRAILING_COMMA.sub(r"\1", payload)):
        try:
            value = json.loads(attempt)
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict):
            raise AnswerFormatError("model output is not a JSON object")
        return value
    raise AnswerFormatError("model output is not valid JSON")


def parse_answer(text: str) -> AnswerDraft:
    payload = parse_json_object(text)
    answer = payload.get("answer")
    citations = payload.get("citations")
    confidence = payload.get("confidence")
    escalate = payload.get("escalate")
    reason = payload.get("reason")

    if not isinstance(answer, str) or not answer.strip():
        raise AnswerFormatError("answer must be a non-empty string")
    if len(answer) > 1500:
        raise AnswerFormatError("answer exceeds 1500 characters")
    if not isinstance(citations, list) or len(citations) > 5:
        raise AnswerFormatError("citations must be a list of at most 5 items")
    if not all(isinstance(item, str) and _CITATION.match(item) for item in citations):
        raise AnswerFormatError("each citation must look like doc_id#index")
    if isinstance(confidence, bool) or not isinstance(confidence, int | float):
        raise AnswerFormatError("confidence must be a number")
    if not 0.0 <= float(confidence) <= 1.0:
        raise AnswerFormatError("confidence must be within [0, 1]")
    if not isinstance(escalate, bool):
        raise AnswerFormatError("escalate must be a boolean")
    if reason not in _ALLOWED_REASONS:
        raise AnswerFormatError(f"unknown reason {reason!r}")

    return AnswerDraft(
        answer=answer.strip(),
        citations=tuple(ChunkId(item) for item in dict.fromkeys(citations)),
        confidence=float(confidence),
        escalate=escalate,
        reason=str(reason),
    )
