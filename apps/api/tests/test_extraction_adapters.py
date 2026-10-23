"""The adapters around extraction: readers, media types, the quality gate, profiles, rendering.

Each test names the property it protects, because these modules are where a silent regression would
poison the corpus rather than fail a request.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from PIL import Image, ImageFilter

from onboarding.app.knowledge.extract.compose import render_document
from onboarding.app.knowledge.extract.media import media_type_for
from onboarding.app.knowledge.extract.pdf import PdfReader
from onboarding.app.knowledge.extract.pptx import PptxReader
from onboarding.app.knowledge.extract.profiles import (
    ExtractionProfileError,
    ExtractionProfileLibrary,
)
from onboarding.app.knowledge.extract.quality import ImageUnreadableError, measure_image
from onboarding.app.knowledge.ingest import CorpusError, load_schema, parse_document
from tests.files import blank_pdf, deck, deck_with_picture, digital_pdf, white_png

ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "docs" / "contracts"
PROFILES = ROOT / "apps" / "api" / "model-profiles" / "extract"


# --- media types -------------------------------------------------------------------------------


def test_the_suffix_decides_for_a_deck_a_browser_cannot_name() -> None:
    assert media_type_for("Политика.pptx", "application/octet-stream").startswith(
        "application/vnd.openxmlformats"
    )


def test_an_unknown_suffix_keeps_a_trusted_declared_type() -> None:
    assert media_type_for("scan", "image/png; charset=binary") == "image/png"


def test_nothing_at_all_becomes_octet_stream() -> None:
    assert media_type_for("", None) == "application/octet-stream"


def test_windows_separators_are_ignored() -> None:
    assert media_type_for(r"C:\Users\hr\reglament.PDF") == "application/pdf"


# --- pdf reader --------------------------------------------------------------------------------


def test_a_digital_pdf_reports_its_text_layer() -> None:
    sniff = PdfReader().inspect(digital_pdf(["First page body"], ["Second page body"]))

    assert sniff.page_count == 2
    assert "First page body" in sniff.pages[0]
    assert "Second page body" in sniff.pages[1]
    assert sniff.encrypted is False


def test_a_scanned_pdf_has_pages_but_no_text() -> None:
    sniff = PdfReader().inspect(blank_pdf(3))

    assert sniff.page_count == 3
    assert all(page.strip() == "" for page in sniff.pages)


def test_a_broken_pdf_is_reported_as_having_no_pages() -> None:
    assert PdfReader().inspect(b"%PDF-1.4 nonsense").page_count == 0


def test_rasterizing_produces_one_png_per_page() -> None:
    images = PdfReader().rasterize(blank_pdf(2), dpi=150)

    assert len(images) == 2
    assert images[0].startswith(b"\x89PNG")


def test_the_reader_claims_pdf_and_nothing_else() -> None:
    reader = PdfReader()

    assert reader.supports("application/pdf")
    assert not reader.supports("image/png")


# --- pptx reader -------------------------------------------------------------------------------


def test_slide_text_keeps_reading_order() -> None:
    sniff = PptxReader().inspect(deck(["Первый блок", "Второй блок"], ["Третий блок"]))

    assert sniff.page_count == 2
    assert sniff.pages[0].split("\n\n") == ["Первый блок", "Второй блок"]
    assert sniff.pages[1] == "Третий блок"


def test_a_deck_of_text_rasterizes_nothing() -> None:
    assert PptxReader().rasterize(deck(["Только текст"]), dpi=300) == ()


def test_an_embedded_picture_reaches_the_recognizer() -> None:
    images = PptxReader().rasterize(deck_with_picture(white_png()), dpi=300)

    assert len(images) == 1
    assert images[0].startswith(b"\x89PNG")


def test_a_broken_deck_is_reported_as_having_no_pages() -> None:
    assert PptxReader().inspect(b"not a zip").page_count == 0


# --- quality gate ------------------------------------------------------------------------------


def test_a_blank_white_page_has_no_high_frequency_detail() -> None:
    metrics = measure_image(white_png(), dpi=300)

    assert metrics.edge_energy == pytest.approx(0.0)
    assert metrics.width == 400
    assert metrics.dpi == 300


def test_sharp_text_scores_higher_than_the_same_page_blurred() -> None:
    """The blur proxy only orders two rasters of one page; it claims no absolute value."""
    reader = PdfReader()
    page = reader.rasterize(digital_pdf(["Line of text here", "and another line"]), dpi=150)[0]
    blurred = _blur(page)

    assert measure_image(page, dpi=150).edge_energy > measure_image(blurred, dpi=150).edge_energy


def _blur(content: bytes, radius: int = 3) -> bytes:
    buffer = io.BytesIO()
    Image.open(io.BytesIO(content)).filter(ImageFilter.GaussianBlur(radius)).save(
        buffer, format="PNG"
    )
    return buffer.getvalue()


def test_undecodable_bytes_raise_instead_of_guessing() -> None:
    with pytest.raises(ImageUnreadableError):
        measure_image(b"definitely not an image", dpi=300)


# --- profiles ----------------------------------------------------------------------------------


def library(root: Path = PROFILES) -> ExtractionProfileLibrary:
    return ExtractionProfileLibrary(root, CONTRACTS / "extraction-profile.schema.json")


def test_the_shipped_profiles_load_and_differ() -> None:
    profiles = library()

    assert set(profiles.available()) >= {"native", "doc-scan"}
    native = profiles.load("native")
    scan = profiles.load("doc-scan")

    assert native.family == "none"
    assert scan.family == "rapid"
    assert native.fingerprint() != scan.fingerprint()


def test_the_fingerprint_ignores_the_description_but_tracks_the_thresholds() -> None:
    first = library().load("doc-scan")
    second = library().load("doc-scan")

    assert first.fingerprint() == second.fingerprint()
    assert first.fingerprint() != library().load("native").fingerprint()


def test_a_missing_profile_lists_the_known_ones() -> None:
    with pytest.raises(ExtractionProfileError, match="known profiles"):
        library().load("nope")


def test_a_profile_named_differently_than_its_file_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "wrong.yaml").write_text(
        "name: other\nfamily: none\nmodel: ''\nlang: ru\ndpi: 300\nmin_text_chars: 40\n"
        "quality: {min_dpi: null, min_edge_energy: null}\n"
        "acceptance: {min_confidence: 0.0, min_chars: 40}\n",
        encoding="utf-8",
    )

    with pytest.raises(ExtractionProfileError, match="but the file is"):
        library(tmp_path).load("wrong")


def test_a_profile_that_violates_its_contract_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "bad.yaml").write_text("name: bad\nfamily: wizard\n", encoding="utf-8")

    with pytest.raises(ExtractionProfileError, match=r"bad\.yaml"):
        library(tmp_path).load("bad")


def test_a_traversal_attempt_never_reaches_the_filesystem() -> None:
    with pytest.raises(ExtractionProfileError, match="invalid extraction profile name"):
        library().load("../native")


def test_the_shipped_profiles_are_valid_json_schema() -> None:
    """A profile is data, so its schema has to be checkable without starting the service."""
    schema = json.loads((CONTRACTS / "extraction-profile.schema.json").read_text(encoding="utf-8"))

    assert schema["required"] == ["name", "family"]
    assert "none" in schema["properties"]["family"]["enum"]


# --- rendering ---------------------------------------------------------------------------------


def test_rendered_markdown_passes_the_same_contract_as_a_committed_document() -> None:
    metadata = {
        "id": "hr/uploaded",
        "title": "Регламент",
        "type": "knowledge",
        "status": "active",
        "owner": "hr-team",
        "audience": ["all"],
        "valid_from": "2026-01-01",
    }

    text = render_document(metadata, "Первый абзац.\nВторой абзац.")
    loaded = parse_document(text, load_schema(CONTRACTS / "doc.schema.json"), source="upload")

    assert loaded.document.id == "hr/uploaded"
    assert "Первый абзац." in loaded.document.text


def test_metadata_missing_a_required_field_fails_the_contract() -> None:
    text = render_document({"id": "hr/x", "title": "X"}, "body")
    schema = load_schema(CONTRACTS / "doc.schema.json")

    with pytest.raises(CorpusError):
        parse_document(text, schema, source="upload")


def test_an_empty_body_is_refused_before_it_becomes_a_document() -> None:
    with pytest.raises(ValueError, match="body is empty"):
        render_document({"id": "hr/x"}, "   ")


def test_empty_metadata_is_refused() -> None:
    with pytest.raises(ValueError, match="metadata is empty"):
        render_document({"text": "ignored"}, "body")
