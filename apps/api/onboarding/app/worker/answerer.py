"""The answer pipeline: retrieve, render, generate, verify, escalate.

Retrieval and validation are deterministic. The model proposes; the code disposes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from onboarding.app.audit import NullAudit
from onboarding.app.copy import Copy
from onboarding.app.llm.gateway import LLMResponseError
from onboarding.app.llm.output import AnswerFormatError, parse_answer
from onboarding.app.prompts import PromptLibrary
from onboarding.app.settings import Settings
from onboarding.core.grounding import judge
from onboarding.core.models import (
    ChunkId,
    EmployeeProfile,
    EscalationReason,
    ScoredChunk,
    Verdict,
)
from onboarding.ports import (
    LLM,
    AuditLog,
    Completion,
    CompletionRequest,
    KnowledgeBase,
    KnowledgeUnavailableError,
    LLMUnavailableError,
    Message,
    Reranker,
    RerankUnavailableError,
    SearchQuery,
)

PROMPT_NAME = "answer"
PROMPT_VERSION = 2


@dataclass(frozen=True, slots=True)
class AnswerOutcome:
    text: str
    escalated: bool
    reason: str
    citations: tuple[ChunkId, ...]
    retrieved: tuple[ScoredChunk, ...]
    completion: Completion | None = None


class Answerer:
    def __init__(
        self,
        *,
        knowledge: KnowledgeBase,
        llm: LLM,
        prompts: PromptLibrary,
        copy: Copy,
        settings: Settings,
        audit: AuditLog | None = None,
        reranker: Reranker | None = None,
    ) -> None:
        self._knowledge = knowledge
        self._llm = llm
        self._prompts = prompts
        self._copy = copy
        self._settings = settings
        self._audit = audit or NullAudit()
        self._reranker = reranker

    async def answer(
        self,
        question: str,
        profile: EmployeeProfile,
        on_date: date,
    ) -> AnswerOutcome:
        normalized = " ".join(question.split())[: self._settings.max_question_chars]
        if not normalized:
            return self._escalate(EscalationReason.NO_SOURCES, ())

        try:
            retrieved = await self._knowledge.search(
                SearchQuery(
                    text=normalized,
                    audience=profile.audience,
                    on_date=on_date,
                    limit=self._settings.recall_limit,
                )
            )
        except KnowledgeUnavailableError:
            return self._escalate(EscalationReason.UNAVAILABLE, ())
        if not retrieved:
            return self._escalate(EscalationReason.NO_SOURCES, ())

        retrieved = await self._rerank(normalized, retrieved)
        return await self._generate(normalized, profile, on_date, retrieved)

    async def _rerank(
        self, question: str, retrieved: tuple[ScoredChunk, ...]
    ) -> tuple[ScoredChunk, ...]:
        """Reorder the candidates; a reranker outage keeps the hybrid order untouched."""
        if self._reranker is None or len(retrieved) < 2:
            return retrieved
        try:
            order = await self._reranker.rerank(
                question,
                tuple(chunk.chunk.text for chunk in retrieved),
                top_n=self._settings.rerank_limit,
            )
        except RerankUnavailableError:
            await self._audit.record("rerank_failed", retrieved=len(retrieved))
            return retrieved
        if not order:
            return retrieved
        reordered = tuple(retrieved[index] for index in order if 0 <= index < len(retrieved))
        await self._audit.record(
            "rerank_completed",
            model=self._settings.rerank_model,
            candidates=len(retrieved),
            kept=len(reordered),
        )
        return reordered

    async def _generate(
        self,
        question: str,
        profile: EmployeeProfile,
        on_date: date,
        retrieved: tuple[ScoredChunk, ...],
    ) -> AnswerOutcome:
        prompt = self._prompts.load(PROMPT_NAME, PROMPT_VERSION)
        rendered = prompt.render(
            {
                "employee_name": profile.name,
                "role": profile.role,
                "department": profile.department,
                "onboarding_day": str(profile.onboarding_day(on_date)),
                "question": question,
                "context": _render_context(retrieved[: self._settings.rerank_limit]),
            }
        )

        try:
            completion = await self._llm.complete(
                CompletionRequest(
                    messages=(Message(role="system", content=rendered),),
                    temperature=prompt.temperature,
                    max_tokens=self._settings.llm_max_tokens,
                    prompt_name=PROMPT_NAME,
                    prompt_version=PROMPT_VERSION,
                    timeout_s=self._settings.llm_timeout_s,
                )
            )
        except (LLMUnavailableError, LLMResponseError):
            await self._audit.record(
                "answer_unavailable",
                retrieved=len(retrieved),
                prompt_version=PROMPT_VERSION,
            )
            return self._escalate(EscalationReason.UNAVAILABLE, retrieved)

        try:
            draft = parse_answer(completion.text)
        except AnswerFormatError:
            await self._audit.record(
                "answer_rejected",
                reason="format",
                retrieved=len(retrieved),
                prompt_version=PROMPT_VERSION,
            )
            return self._escalate(EscalationReason.NO_SOURCES, retrieved, completion)

        verdict = judge(
            draft,
            {chunk.chunk.id for chunk in retrieved},
            min_confidence=self._settings.answer_min_confidence,
        )
        await self._audit.record(
            "answer_completed",
            accepted=verdict.accepted,
            reason=verdict.reason,
            citations=len(verdict.citations),
            retrieved=len(retrieved),
            prompt_version=PROMPT_VERSION,
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
            cost_rub=completion.cost_rub,
            latency_ms=completion.latency_ms,
        )

        if verdict.accepted and not draft.escalate:
            return AnswerOutcome(
                text=verdict.answer,
                escalated=False,
                reason=verdict.reason,
                citations=verdict.citations,
                retrieved=retrieved,
                completion=completion,
            )

        reason = _escalation_reason(verdict)
        return AnswerOutcome(
            text=self._copy.escalation_for(reason) + "\n\n" + self._copy.escalation_footer,
            escalated=True,
            reason=reason.value,
            citations=(),
            retrieved=retrieved,
            completion=completion,
        )

    def _escalate(
        self,
        reason: EscalationReason,
        retrieved: tuple[ScoredChunk, ...],
        completion: Completion | None = None,
    ) -> AnswerOutcome:
        return AnswerOutcome(
            text=self._copy.escalation_for(reason) + "\n\n" + self._copy.escalation_footer,
            escalated=True,
            reason=reason.value,
            citations=(),
            retrieved=retrieved,
            completion=completion,
        )


def _render_context(chunks: tuple[ScoredChunk, ...]) -> str:
    return (
        "\n".join(
            f'<doc id="{chunk.chunk.id}" source="{chunk.chunk.doc_id}">{chunk.chunk.text}</doc>'
            for chunk in chunks
        )
        or "<doc/>"
    )


def _escalation_reason(verdict: Verdict) -> EscalationReason:
    try:
        return EscalationReason(verdict.reason)
    except ValueError:
        return EscalationReason.NO_SOURCES
