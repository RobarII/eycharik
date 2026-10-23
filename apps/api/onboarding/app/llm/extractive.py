"""Deterministic extractive provider for offline demos and retrieval tests.

It answers from the same prompt the real model receives, so the whole pipeline (rendering,
grounding, citation validation, audit) is exercised without a network call. It is not a language
model and it must never run in production: ``Settings`` rejects it when ``ENVIRONMENT`` is
``production``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from onboarding.core.models import EscalationReason
from onboarding.ports import Completion, CompletionRequest

DOC = re.compile(
    r'<doc id="(?P<id>[^"]+)" source="(?P<source>[^"]+)">(?P<text>.*?)</doc>',
    re.DOTALL,
)
QUESTION = re.compile(r"# Вопрос сотрудника\s*\n\s*(?P<question>.+?)\s*\n\s*# Фрагменты", re.DOTALL)
WORD = re.compile(r"[а-яёa-z0-9]{4,}")

RESTRICTED = (
    "мой наставник",
    "моя зарплата",
    "мою зарплату",
    "у меня будет зарплата",
    "у меня зарплата",
    "мой оклад",
    "мой договор",
    "договор со мной",
    "конфликт с",
    "по здоровью",
    "со здоровьем",
    "увольнен",
    "штраф",
)
INJECTION = (
    "игнорируй",
    "системный промпт",
    "покажи промпт",
    "print your prompt",
    "ignore your instructions",
)
STOP = frozenset(
    {
        "какой",
        "какая",
        "какие",
        "сколько",
        "нужно",
        "можно",
        "быть",
        "этого",
        "чтобы",
        "также",
        "свой",
        "свои",
        "меня",
        "мне",
        "если",
        "или",
        "для",
    }
)


@dataclass(frozen=True, slots=True)
class ExtractiveLLM:
    """Pick the fragment that best overlaps the question and quote it with a citation."""

    min_score: int = 1
    max_chars: int = 700

    async def complete(self, request: CompletionRequest) -> Completion:
        prompt = "\n".join(message.content for message in request.messages)
        question = _question(prompt)
        lowered = question.lower()

        if any(marker in lowered for marker in INJECTION):
            return _completion(_payload(EscalationReason.OUT_OF_SCOPE, escalate=True), prompt)

        docs = [(match["id"], _clean(match["text"])) for match in DOC.finditer(prompt)]
        if not docs:
            return _completion(_payload(EscalationReason.NO_SOURCES, escalate=True), prompt)

        if any(marker in lowered for marker in RESTRICTED):
            return _completion(_payload(EscalationReason.RESTRICTED, escalate=True), prompt)

        terms = _terms(question)
        scored = sorted(
            ((len(terms & _terms(text)), doc_id, text) for doc_id, text in docs),
            key=lambda item: item[0],
            reverse=True,
        )
        score, doc_id, text = scored[0]
        if score < self.min_score:
            return _completion(_payload(EscalationReason.NO_SOURCES, escalate=True), prompt)

        answer = _sentences(text, terms, max_chars=self.max_chars)
        if not answer:
            return _completion(_payload(EscalationReason.NO_SOURCES, escalate=True), prompt)

        confidence = 0.82 if score >= 2 else 0.58
        payload = {
            "answer": f"{answer} [{doc_id}]",
            "citations": [doc_id],
            "confidence": confidence,
            "escalate": False,
            "reason": "answered",
        }
        return _completion(payload, prompt)


def _payload(reason: EscalationReason, *, escalate: bool) -> dict[str, object]:
    return {
        "answer": "Передам вопрос рекрутеру.",
        "citations": [],
        "confidence": 0.0,
        "escalate": escalate,
        "reason": reason.value,
    }


def _completion(payload: dict[str, object], prompt: str) -> Completion:
    tokens = max(1, len(prompt) // 4)
    return Completion(
        text=json.dumps(payload, ensure_ascii=False),
        model="extractive",
        input_tokens=tokens,
        output_tokens=max(1, len(str(payload)) // 4),
        latency_ms=0,
        cost_rub=0.0,
    )


def _question(prompt: str) -> str:
    match = QUESTION.search(prompt)
    if match is None:
        raise ValueError(
            "extractive provider: no question block; update DOC/QUESTION together with the prompt"
        )
    return match["question"].strip()


def _terms(text: str) -> set[str]:
    return {
        word
        for word in (match.group(0) for match in WORD.finditer(text.lower()))
        if word not in STOP
    }


def _clean(text: str) -> str:
    """Drop Markdown headings and bullets: they are labels, not answers."""
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith(("#", "-", "*"))
    ]
    return " ".join(lines)


def _sentences(text: str, terms: set[str], *, max_chars: int) -> str:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]
    ranked = sorted(
        enumerate(parts),
        key=lambda item: (len(terms & _terms(item[1])), -item[0]),
        reverse=True,
    )
    chosen = [index for index, _ in ranked[:2] if terms & _terms(parts[index])]
    if not chosen:
        chosen = list(range(min(2, len(parts))))
    result = " ".join(parts[index] for index in sorted(chosen))
    return result[:max_chars].strip()
