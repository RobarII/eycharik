"""The pure half of extraction: routing, the quality gate, normalization, and acceptance.

No database, no files, no patching. Each test states one rule of the module docstring.
"""

from __future__ import annotations

import pytest

from onboarding.core.extraction import accept, assemble, assess, normalize, refusal, refused, route
from onboarding.core.models import (
    AcceptancePolicy,
    Accepted,
    DocumentSniff,
    ExtractedPage,
    ExtractionRoute,
    ImageMetrics,
    QualityPolicy,
    Rejected,
    RejectionReason,
)


def page(text: str, *, confidence: float = 1.0, index: int = 0) -> ExtractedPage:
    return ExtractedPage(
        index=index, text=text, confidence=confidence, engine="e", route=ExtractionRoute.NATIVE_TEXT
    )


# --- refusal -----------------------------------------------------------------------------------


def test_encrypted_file_is_refused_before_anything_else() -> None:
    sniff = DocumentSniff(page_count=4, pages=("text",), encrypted=True)

    assert refusal(sniff) is RejectionReason.ENCRYPTED


def test_a_file_without_pages_is_refused() -> None:
    assert refusal(DocumentSniff(page_count=0)) is RejectionReason.NO_PAGES


def test_a_readable_file_is_not_refused() -> None:
    assert refusal(DocumentSniff(page_count=1, pages=("x",))) is None


# --- routing -----------------------------------------------------------------------------------


@pytest.mark.parametrize("chars", [40, 41, 5_000])
def test_a_text_layer_wins_even_when_shortish(chars: int) -> None:
    sniff = DocumentSniff(page_count=1, pages=("x" * chars,))

    assert route(sniff, min_text_chars=40) is ExtractionRoute.NATIVE_TEXT


def test_no_text_layer_means_recognition() -> None:
    sniff = DocumentSniff(page_count=2, pages=("", " "))

    assert route(sniff, min_text_chars=40) is ExtractionRoute.OCR


def test_encryption_beats_recognition() -> None:
    sniff = DocumentSniff(page_count=2, pages=(), encrypted=True)

    assert route(sniff, min_text_chars=40) is ExtractionRoute.REJECTED


def test_empty_file_is_rejected_not_recognized() -> None:
    assert route(DocumentSniff(page_count=0), min_text_chars=40) is ExtractionRoute.REJECTED


def test_one_page_of_text_layer_is_enough_to_skip_ocr() -> None:
    """A digital page next to a scanned one is still a digital document; the scan is spared."""
    sniff = DocumentSniff(page_count=2, pages=("x" * 100, ""))

    assert route(sniff, min_text_chars=40) is ExtractionRoute.NATIVE_TEXT


# --- quality gate ------------------------------------------------------------------------------


def test_unmeasured_metrics_never_refuse() -> None:
    assert assess(ImageMetrics(), QualityPolicy()).ok


def test_low_dpi_is_refused() -> None:
    verdict = assess(ImageMetrics(dpi=100), QualityPolicy(min_dpi=200))

    assert verdict.reasons == (RejectionReason.LOW_DPI,)


def test_a_washed_out_page_is_not_refused_before_recognition() -> None:
    """Glare has no honest pre-recognition metric: white paper is "100% glare".

    Overexposure is caught after recognition, by the engine's own confidence.
    """
    assert assess(ImageMetrics(edge_energy=900.0), QualityPolicy()).ok


def test_blur_proxy_is_refused_only_when_a_threshold_exists() -> None:
    metrics = ImageMetrics(edge_energy=3.0)

    assert assess(metrics, QualityPolicy(min_edge_energy=None)).ok
    assert assess(metrics, QualityPolicy(min_edge_energy=10.0)).reasons == (RejectionReason.BLURRY,)


def test_every_failed_check_is_reported() -> None:
    metrics = ImageMetrics(dpi=10, edge_energy=0.1)
    verdict = assess(metrics, QualityPolicy(min_dpi=200, min_edge_energy=5))

    assert verdict.ok is False
    assert verdict.reasons == (RejectionReason.LOW_DPI, RejectionReason.BLURRY)
    assert verdict.reason is RejectionReason.LOW_DPI


# --- normalization -----------------------------------------------------------------------------


def test_a_hyphenated_line_break_is_joined() -> None:
    assert normalize("рег-\nламент") == "регламент"


def test_a_hyphen_before_a_capital_stays() -> None:
    assert normalize("Санкт-\nПетербург") == "Санкт-\nПетербург"


def test_ligatures_and_exotic_spaces_are_normalized() -> None:
    assert normalize("e\ufb03cient\u00a0work") == "efficient work"


def test_whitespace_and_blank_lines_collapse() -> None:
    assert normalize("  a  \t b  \n\n\n\n c ") == "a b\n\nc"


def test_digits_are_never_rewritten() -> None:
    """An OCR guess "fixed" by a rule is a fabricated fact, so the text passes through."""
    assert normalize("ИНН 7707083893, сумма 1 234,50 ₽") == "ИНН 7707083893, сумма 1 234,50 ₽"


def test_normalization_is_idempotent() -> None:
    once = normalize("рег-\nламент  о\n\n\n\nперсонале")

    assert normalize(once) == once


# --- assembling --------------------------------------------------------------------------------


def test_pages_are_renumbered_and_inherit_the_engine() -> None:
    document = assemble(
        [ExtractedPage(index=9, text="a"), ExtractedPage(index=7, text="b")],
        engine="pdfium",
        content_hash="h",
        route=ExtractionRoute.NATIVE_TEXT,
        profile="native",
        profile_hash="p",
    )

    assert [item.index for item in document.pages] == [0, 1]
    assert {item.engine for item in document.pages} == {"pdfium"}
    assert document.content_hash == "h"
    assert document.refusal is None


def test_a_refusal_carries_its_reason_and_no_pages() -> None:
    document = refused(
        RejectionReason.ENCRYPTED, engine="pdfium", content_hash="h", profile="native"
    )

    assert document.pages == ()
    assert document.route is ExtractionRoute.REJECTED
    assert document.refusal is RejectionReason.ENCRYPTED


# --- acceptance --------------------------------------------------------------------------------


def test_accepted_text_joins_pages_with_a_blank_line() -> None:
    document = assemble(
        [page("первый абзац"), page("второй абзац")],
        engine="pdfium",
        content_hash="h",
        route=ExtractionRoute.NATIVE_TEXT,
    )

    outcome = accept(document, AcceptancePolicy(min_chars=10))

    assert isinstance(outcome, Accepted)
    assert outcome.text == "первый абзац\n\nвторой абзац"
    assert outcome.pages == 2


def test_a_refused_document_is_never_accepted() -> None:
    document = refused(RejectionReason.NO_PAGES, engine="pdfium", content_hash="h")

    outcome = accept(document, AcceptancePolicy())

    assert isinstance(outcome, Rejected)
    assert outcome.reason is RejectionReason.NO_PAGES


def test_a_page_without_text_is_dropped_but_an_empty_document_is_refused() -> None:
    document = assemble(
        [page(""), page("  ")],
        engine="pdfium",
        content_hash="h",
        route=ExtractionRoute.NATIVE_TEXT,
    )

    outcome = accept(document, AcceptancePolicy())

    assert isinstance(outcome, Rejected)
    assert outcome.reason is RejectionReason.EMPTY


def test_one_low_confidence_page_refuses_the_document() -> None:
    """Half an indexed document answers wrongly with confidence, so it is not indexed at all."""
    document = assemble(
        [page("первая страница целиком", confidence=0.95), page("вторая", confidence=0.4)],
        engine="rapidocr",
        content_hash="h",
        route=ExtractionRoute.OCR,
    )

    outcome = accept(document, AcceptancePolicy(min_confidence=0.72))

    assert isinstance(outcome, Rejected)
    assert outcome.reason is RejectionReason.LOW_CONFIDENCE
    assert outcome.page == 1


def test_short_text_is_refused() -> None:
    document = assemble(
        [page("да")], engine="pdfium", content_hash="h", route=ExtractionRoute.NATIVE_TEXT
    )

    outcome = accept(document, AcceptancePolicy(min_chars=40))

    assert isinstance(outcome, Rejected)
    assert outcome.reason is RejectionReason.TOO_SHORT


def test_acceptance_reports_the_worst_page_confidence() -> None:
    document = assemble(
        [page("a" * 30, confidence=0.9), page("b" * 30, confidence=0.75)],
        engine="rapidocr",
        content_hash="h",
        route=ExtractionRoute.OCR,
    )

    outcome = accept(document, AcceptancePolicy(min_confidence=0.7, min_chars=10))

    assert isinstance(outcome, Accepted)
    assert outcome.min_confidence == pytest.approx(0.75)
