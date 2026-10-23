"""Deterministic answer validation.

The model proposes an answer with citations; this module decides whether it may be sent. A citation
that was not retrieved for this question means the answer is ungrounded, no matter how confident
the model sounds. The check is code, not a second model call.
"""

from __future__ import annotations

from collections.abc import Collection

from .models import AnswerDraft, ChunkId, RefusalReason, Verdict


def judge(
    draft: AnswerDraft,
    retrieved: Collection[ChunkId],
    *,
    min_confidence: float,
) -> Verdict:
    """Accept a grounded answer or turn the response into an escalation."""
    if draft.escalate:
        return Verdict(
            accepted=True,
            reason=draft.reason,
            answer=draft.answer,
            citations=(),
        )

    if not draft.citations:
        return _refuse(draft, RefusalReason.NO_SOURCES)

    unseen = tuple(citation for citation in draft.citations if citation not in retrieved)
    if unseen:
        return _refuse(draft, RefusalReason.NO_SOURCES)

    if not 0.0 <= draft.confidence <= 1.0:
        raise ValueError(f"confidence out of range: {draft.confidence!r}")
    if draft.confidence < min_confidence:
        return _refuse(draft, RefusalReason.LOW_CONFIDENCE)

    return Verdict(
        accepted=True,
        reason="answered",
        answer=draft.answer,
        citations=draft.citations,
    )


def _refuse(draft: AnswerDraft, reason: RefusalReason) -> Verdict:
    return Verdict(
        accepted=False,
        reason=reason.value,
        answer=draft.answer,
        citations=(),
    )
