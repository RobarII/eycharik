"""The routing composite: bytes in, a document or a refusal out, effects sequenced only.

The engine is a fake. Routing is the interesting decision, and it has to be visible in the result
without a real recognizer: a digital PDF must never pay for OCR, and a scan must never be guessed.
"""

from __future__ import annotations

import hashlib

import pytest

from onboarding.app.knowledge.extract.ocr import UnavailableOcr
from onboarding.app.knowledge.extract.pdf import PdfReader
from onboarding.app.knowledge.extract.pptx import PptxReader
from onboarding.app.knowledge.extract.router import RoutingExtraction
from onboarding.core.models import (
    AcceptancePolicy,
    ExtractedPage,
    ExtractionRoute,
    QualityPolicy,
    RejectionReason,
)
from onboarding.ports import (
    DocumentRef,
    ExtractionProfile,
    ExtractionUnavailableError,
)
from tests.fakes import FakeOcr
from tests.files import blank_pdf, deck, deck_with_picture, digital_pdf, white_png

PDF = "application/pdf"
PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def profile(**overrides: object) -> ExtractionProfile:
    values: dict[str, object] = {
        "name": "test",
        "family": "rapid",
        "model": "pp-ocrv5-cyrillic",
        "lang": "ru",
        "dpi": 300,
        "min_text_chars": 40,
        "quality": QualityPolicy(),
        "acceptance": AcceptancePolicy(),
    }
    values.update(overrides)
    return ExtractionProfile(**values)  # type: ignore[arg-type]


def ref(media_type: str = PDF) -> DocumentRef:
    return DocumentRef(blob_id="b", filename="f", media_type=media_type)


def router(ocr: FakeOcr | UnavailableOcr, *, max_pages: int = 200) -> RoutingExtraction:
    return RoutingExtraction(readers=(PdfReader(), PptxReader()), ocr=ocr, max_pages=max_pages)


def recognized(text: str = "распознанный текст страницы", confidence: float = 0.94) -> FakeOcr:
    return FakeOcr(pages=(ExtractedPage(index=0, text=text, confidence=confidence),))


async def test_a_digital_pdf_never_touches_the_recognizer() -> None:
    ocr = recognized()

    document = await router(ocr).extract(
        digital_pdf(["Digital body text, long enough to be trusted as a text layer"]),
        ref(),
        profile(),
    )

    assert document.route is ExtractionRoute.NATIVE_TEXT
    assert document.engine == "pdfium"
    assert "Digital body text" in document.pages[0].text
    assert ocr.calls == []


async def test_a_deck_is_read_as_text() -> None:
    document = await router(recognized()).extract(
        deck(["Слайд с достаточным количеством текста для текстового слоя"]),
        ref(PPTX),
        profile(),
    )

    assert document.route is ExtractionRoute.NATIVE_TEXT
    assert document.engine == "python-pptx"
    assert document.pages[0].text.startswith("Слайд с достаточным")


async def test_a_scan_is_recognized_with_the_profile_language_and_model() -> None:
    ocr = recognized()

    document = await router(ocr).extract(
        blank_pdf(), ref(), profile(quality=QualityPolicy(min_dpi=None))
    )

    assert document.route is ExtractionRoute.OCR
    assert document.engine == "fake-ocr"
    assert document.pages[0].confidence == pytest.approx(0.94)
    assert ocr.calls == [(1, "ru", "pp-ocrv5-cyrillic")]


async def test_a_deck_of_screenshots_is_recognized() -> None:
    document = await router(recognized()).extract(
        deck_with_picture(white_png()), ref(PPTX), profile(quality=QualityPolicy(min_dpi=None))
    )

    assert document.route is ExtractionRoute.OCR


async def test_without_a_recognizer_a_scan_fails_loudly() -> None:
    """A missing dependency is a deployment error, not a reader's opinion; it must be visible."""
    with pytest.raises(ExtractionUnavailableError):
        await router(UnavailableOcr()).extract(
            blank_pdf(), ref(), profile(quality=QualityPolicy(min_dpi=None))
        )


async def test_an_unsupported_format_is_refused_not_guessed() -> None:
    document = await router(recognized()).extract(b"\x89PNG", ref("image/png"), profile())

    assert document.refusal is RejectionReason.UNSUPPORTED
    assert document.pages == ()
    assert document.engine == "none"


async def test_the_quality_gate_stops_a_blurred_page_before_recognition() -> None:
    ocr = recognized()
    strict = profile(quality=QualityPolicy(min_dpi=None, min_edge_energy=100.0))

    document = await router(ocr).extract(blank_pdf(), ref(), strict)

    assert document.refusal is RejectionReason.BLURRY
    assert ocr.calls == []


async def test_a_document_over_the_page_budget_is_refused() -> None:
    document = await router(recognized(), max_pages=1).extract(
        blank_pdf(2), ref(), profile(quality=QualityPolicy(min_dpi=None))
    )

    assert document.refusal is RejectionReason.TOO_MANY_PAGES


async def test_a_broken_file_is_refused_as_having_no_pages() -> None:
    document = await router(recognized()).extract(b"%PDF-1.4 nothing", ref(), profile())

    assert document.refusal is RejectionReason.NO_PAGES


async def test_the_document_carries_the_hash_of_the_bytes() -> None:
    content = digital_pdf(["Body"])

    document = await router(recognized()).extract(content, ref(), profile())

    assert document.content_hash == hashlib.sha256(content).hexdigest()
    assert document.profile == "test"
    assert document.profile_hash == profile().fingerprint()
    assert document.profile_hash != profile(dpi=150).fingerprint()
