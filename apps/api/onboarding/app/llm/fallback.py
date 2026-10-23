"""The keyword fallback: one policy, one audit event, one set of limits.

A model outage lowers precision, never availability (ADR 0011). Two classifiers implement that
promise, so the promise lives in one place: both call :func:`fallback_signal` instead of keeping a
copy. The limits are the ones the sentiment contract states, and a test pins them to
``docs/contracts/sentiment.schema.json`` so a code constant cannot drift from the schema.
"""

from __future__ import annotations

from onboarding.app.audit import NullAudit
from onboarding.core.models import RiskSignal, SignalTag
from onboarding.core.risk import keyword_signal
from onboarding.ports import AuditLog

MAX_ANSWER_CHARS = 2000
MAX_TAGS = 3
TAGS = {tag.value: tag for tag in SignalTag}


async def fallback_signal(
    audit: AuditLog | None,
    text: str,
    source: str,
    *,
    provider: str,
    reason: str,
) -> RiskSignal:
    """Audit why the model did not answer, then label with the deterministic classifier."""
    await (audit or NullAudit()).record(
        "sentiment_fallback", source=source, provider=provider, reason=reason
    )
    return keyword_signal(text, source=source)


class KeywordSentiment:
    """The deterministic classifier as a :class:`SentimentAnalysis`, for the eval baseline."""

    async def classify(self, text: str, *, source: str) -> RiskSignal:
        return keyword_signal(text, source=source)


__all__ = ["MAX_ANSWER_CHARS", "MAX_TAGS", "TAGS", "KeywordSentiment", "fallback_signal"]
