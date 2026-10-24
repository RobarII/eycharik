"""Deterministic answer validation.

The model proposes an answer with citations; this module decides whether it may be sent. A citation
that was not retrieved for this question means the answer is ungrounded, no matter how confident
the model sounds. The check is code, not a second model call.
"""

from __future__ import annotations

import re
from collections.abc import Collection

from .models import AnswerDraft, ChunkId, RefusalReason, Verdict

_INLINE_CITATION = re.compile(r"\[([^\[\]\s]+)\]")


def inline_citations(answer: str) -> tuple[str, ...]:
    """Document ids the model wrote inside the answer text, in order, without duplicates."""
    tokens = (match.group(1) for match in _INLINE_CITATION.finditer(answer))
    return tuple(dict.fromkeys(token for token in tokens if "#" in token or "/" in token))


def with_citations(answer: str, citations: Collection[ChunkId]) -> str:
    """Make every accepted citation visible in the message the employee receives.

    The model is asked to write ``[id]`` inline, but a provider may put ids only in the JSON
    ``citations`` field. An answer without an inline source is still grounded; hiding that source
    from the employee is not acceptable, so the missing ids are appended once.
    """
    seen = frozenset(inline_citations(answer))
    missing = tuple(dict.fromkeys(citation for citation in citations if citation not in seen))
    if not missing:
        return answer
    suffix = " ".join(f"[{citation}]" for citation in missing)
    return f"{answer.rstrip()} {suffix}"


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
    invented = tuple(
        citation for citation in inline_citations(draft.answer) if citation not in retrieved
    )
    if invented:
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
