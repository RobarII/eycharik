"""Decisions about a file that arrived as a document.

Four questions, four pure functions, no I/O:

``refusal``  — is this file readable at all (encrypted, empty, unsupported)?
``route``    — does the text layer suffice, or does it need recognition?
``assess``   — is the raster worth feeding to an engine?
``accept``   — is the result good enough to index, or is the whole document refused?

A refusal is a value, not an exception: the caller persists the reason and a recruiter reads it.
Half-indexed knowledge is the failure mode this module exists to prevent — one unreadable page
refuses the document instead of silently shrinking it.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from onboarding.core.models import (
    Acceptance,
    AcceptancePolicy,
    Accepted,
    DocumentSniff,
    ExtractedDocument,
    ExtractedPage,
    ExtractionRoute,
    ImageMetrics,
    QualityPolicy,
    QualityVerdict,
    Rejected,
    RejectionReason,
)

_LIGATURES = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\ufb05": "st",
    "\ufb06": "st",
}
_SOFT_HYPHEN = "\u00ad"
_NARROW_SPACES = "\u00a0\u2007\u2008\u2009\u200a\u202f"
_HYPHEN_BREAK = re.compile(r"([^\W\d_])-\n([^\W\d_])")
_MULTI_SPACE = re.compile(r"[ \t]+")
_MULTI_NEWLINE = re.compile(r"\n{3,}")


def refusal(sniff: DocumentSniff) -> RejectionReason | None:
    """Why the file cannot be read at all, or ``None`` when it can."""
    if sniff.encrypted:
        return RejectionReason.ENCRYPTED
    if sniff.page_count <= 0:
        return RejectionReason.NO_PAGES
    return None


def route(sniff: DocumentSniff, *, min_text_chars: int) -> ExtractionRoute:
    """Native text wins: a digital document never pays for recognition, even a blurry one."""
    if refusal(sniff) is not None:
        return ExtractionRoute.REJECTED
    if sniff.text_chars >= min_text_chars:
        return ExtractionRoute.NATIVE_TEXT
    return ExtractionRoute.OCR


def assess(metrics: ImageMetrics, policy: QualityPolicy) -> QualityVerdict:
    """Gate a raster. A metric that is ``None`` was not measured, so its check does not run."""
    reasons: list[RejectionReason] = []
    if policy.min_dpi is not None and metrics.dpi is not None and metrics.dpi < policy.min_dpi:
        reasons.append(RejectionReason.LOW_DPI)
    if (
        policy.min_edge_energy is not None
        and metrics.edge_energy is not None
        and metrics.edge_energy < policy.min_edge_energy
    ):
        reasons.append(RejectionReason.BLURRY)
    return QualityVerdict(ok=not reasons, reasons=tuple(reasons))


def normalize(text: str) -> str:
    """Machine text that reads as the page printed it.

    Line-break hyphenation, ligatures, and exotic spaces are layout artefacts, so they go. Digits
    are never touched: an OCR guess corrected by a rule is a fabricated fact.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for source, target in _LIGATURES.items():
        text = text.replace(source, target)
    text = text.replace(_SOFT_HYPHEN, "")
    for space in _NARROW_SPACES:
        text = text.replace(space, " ")
    text = _join_hyphen_breaks(text)
    lines = [_collapse(line) for line in text.split("\n")]
    return _collapse_newlines("\n".join(lines)).strip()


def assemble(
    pages: Iterable[ExtractedPage],
    *,
    engine: str,
    content_hash: str,
    route: ExtractionRoute,
    profile: str = "",
    profile_hash: str = "",
) -> ExtractedDocument:
    """Renumber pages in reading order. Empty pages are kept: the refusal rules need to see them."""
    ordered = tuple(
        ExtractedPage(
            index=index,
            text=page.text,
            confidence=page.confidence,
            engine=page.engine or engine,
            route=page.route,
        )
        for index, page in enumerate(pages)
    )
    return ExtractedDocument(
        pages=ordered,
        engine=engine,
        content_hash=content_hash,
        route=route,
        profile=profile,
        profile_hash=profile_hash,
    )


def refused(
    reason: RejectionReason,
    *,
    engine: str,
    content_hash: str,
    profile: str = "",
    profile_hash: str = "",
) -> ExtractedDocument:
    """A file that never became text. The reason travels with it to the audit trail."""
    return ExtractedDocument(
        pages=(),
        engine=engine,
        content_hash=content_hash,
        route=ExtractionRoute.REJECTED,
        profile=profile,
        profile_hash=profile_hash,
        refusal=reason,
    )


def accept(document: ExtractedDocument, policy: AcceptancePolicy) -> Acceptance:
    """Turn an extraction into indexable text, or refuse the whole document with a reason."""
    if document.refusal is not None:
        return Rejected(reason=document.refusal, detail="refused before recognition")

    pages = tuple(page for page in document.pages if normalize(page.text))
    if not pages:
        return Rejected(reason=RejectionReason.EMPTY, detail="no page produced text")

    for page in pages:
        if page.confidence < policy.min_confidence:
            return Rejected(
                reason=RejectionReason.LOW_CONFIDENCE,
                page=page.index,
                detail=f"confidence {page.confidence:.2f} below {policy.min_confidence:.2f}",
            )

    text = "\n\n".join(normalize(page.text) for page in pages)
    if len(text) < policy.min_chars:
        return Rejected(
            reason=RejectionReason.TOO_SHORT,
            detail=f"{len(text)} characters below {policy.min_chars}",
        )
    return Accepted(
        text=text,
        pages=len(pages),
        min_confidence=min(page.confidence for page in pages),
    )


def _join_hyphen_breaks(text: str) -> str:
    """``рег-\\nламент`` becomes ``регламент``; ``Санкт-\\nПетербург`` keeps its hyphen."""

    def replace(match: re.Match[str]) -> str:
        head, tail = match.group(1), match.group(2)
        if tail.islower():
            return head + tail
        return match.group(0)

    return _HYPHEN_BREAK.sub(replace, text)


def _collapse(line: str) -> str:
    return _MULTI_SPACE.sub(" ", line).strip()


def _collapse_newlines(text: str) -> str:
    return _MULTI_NEWLINE.sub("\n\n", text)
