"""The ``extract_document`` job: the only place extraction meets the database and the corpus.

An accepted file is indexed through the same choke point as a committed one; a refused file is
recorded and never indexed; a cached file is not read twice.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from onboarding.app.knowledge.embedding import HashingEmbedder
from onboarding.app.knowledge.extract.ocr import UnavailableOcr
from onboarding.app.knowledge.extract.pdf import PdfReader
from onboarding.app.knowledge.extract.pptx import PptxReader
from onboarding.app.knowledge.extract.router import RoutingExtraction
from onboarding.app.worker.extract import INDEXED, REJECTED, DocumentExtractor
from onboarding.app.worker.payload import JobPayloadError
from onboarding.core.extraction import refused
from onboarding.core.models import (
    AcceptancePolicy,
    ExtractedPage,
    QualityPolicy,
    RejectionReason,
)
from onboarding.ports import ExtractionProfile, ExtractionUnavailableError
from tests.fakes import (
    FakeOcr,
    FixedExtraction,
    InMemoryBlobs,
    InMemoryExtractionCache,
    RecordingAudit,
    RecordingKnowledgeWriter,
)
from tests.files import blank_pdf, digital_pdf

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "docs" / "contracts" / "doc.schema.json"
# A base-14 font cannot carry Cyrillic, so this PDF is Latin; recognition tests use Russian.
DIGITAL = digital_pdf(["Internal regulations, page one, long enough to trust"])

METADATA = {
    "id": "hr/uploaded",
    "title": "Регламент",
    "type": "knowledge",
    "status": "active",
    "owner": "hr-team",
    "audience": ["all"],
    "valid_from": "2026-01-01",
}


def profile(**overrides: object) -> ExtractionProfile:
    values: dict[str, object] = {
        "name": "test",
        "family": "rapid",
        "model": "pp-ocrv5-cyrillic",
        "lang": "ru",
        "dpi": 300,
        "min_text_chars": 40,
        "quality": QualityPolicy(min_dpi=None),
        "acceptance": AcceptancePolicy(min_confidence=0.72, min_chars=40),
    }
    values.update(overrides)
    return ExtractionProfile(**values)  # type: ignore[arg-type]


class ExtractJob:
    def __init__(
        self,
        *,
        content: bytes = DIGITAL,
        ocr: FakeOcr | UnavailableOcr | None = None,
        extraction_profile: ExtractionProfile | None = None,
    ) -> None:
        self.blobs = InMemoryBlobs()
        self.cache = InMemoryExtractionCache()
        self.writer = RecordingKnowledgeWriter()
        self.audit = RecordingAudit()
        self.profile = extraction_profile or profile()
        self.extraction = RoutingExtraction(
            readers=(PdfReader(), PptxReader()), ocr=ocr or FakeOcr()
        )
        self.content = content
        self.job = DocumentExtractor(
            blobs=self.blobs,
            extraction=self.extraction,
            cache=self.cache,
            writer=self.writer,
            embedder=HashingEmbedder(dim=8),
            schema_path=SCHEMA,
            profile=self.profile,
            audit=self.audit,
        )

    async def run(self, payload: dict[str, object] | None = None) -> None:
        blob_id = await self.blobs.put(self.content, filename="f.pdf", media_type="application/pdf")
        await self.job.run(
            payload
            or {"blob_id": blob_id, "filename": "f.pdf", "media_type": "application/pdf"}
            | {"metadata": METADATA}
        )


async def test_an_extracted_document_enters_the_corpus_like_any_other() -> None:
    harness = ExtractJob()

    await harness.run()

    assert len(harness.writer.documents) == 1
    record, chunks = harness.writer.documents[0]
    assert str(record.id) == "hr/uploaded"
    assert record.owner == "hr-team"
    assert chunks
    assert "Internal regulations" in chunks[0].text


async def test_the_outcome_is_recorded_for_the_cabinet() -> None:
    harness = ExtractJob()

    await harness.run()

    cached = next(iter(harness.cache.records.values()))
    assert cached.status == INDEXED
    assert cached.reason is None
    assert cached.document_id == "hr/uploaded"
    assert cached.markdown is not None
    assert cached.markdown.startswith("---\n")
    assert harness.audit.names() == ["document_extracted"]


async def test_the_same_bytes_are_never_read_twice() -> None:
    harness = ExtractJob()
    await harness.run()
    blob_id = next(iter(harness.blobs.store))

    await harness.job.run(
        {
            "blob_id": blob_id,
            "filename": "f.pdf",
            "media_type": "application/pdf",
            "metadata": METADATA,
        }
    )

    assert len(harness.writer.documents) == 1
    assert harness.audit.names() == ["document_extracted", "document_extraction_cached"]


async def test_a_different_profile_reads_the_same_bytes_again() -> None:
    """The cache key is (file, profile): a better recognizer must be able to re-read a file."""
    harness = ExtractJob()
    await harness.run()

    harness.profile = profile(dpi=150)
    harness.job = DocumentExtractor(
        blobs=harness.blobs,
        extraction=harness.extraction,
        cache=harness.cache,
        writer=harness.writer,
        embedder=HashingEmbedder(dim=8),
        schema_path=SCHEMA,
        profile=harness.profile,
        audit=harness.audit,
    )
    await harness.job.run(
        {
            "blob_id": next(iter(harness.blobs.store)),
            "filename": "f.pdf",
            "media_type": "application/pdf",
            "metadata": METADATA,
        }
    )

    assert harness.audit.names() == ["document_extracted", "document_extracted"]


async def test_a_scan_without_a_recognizer_is_refused_not_indexed() -> None:
    harness = ExtractJob(content=blank_pdf(), ocr=UnavailableOcr())

    with pytest.raises(ExtractionUnavailableError):
        await harness.run()

    assert harness.writer.documents == []
    assert harness.cache.records == {}


async def test_a_low_confidence_recognition_is_refused_and_recorded() -> None:
    harness = ExtractJob(
        content=blank_pdf(),
        ocr=FakeOcr(
            pages=(
                ExtractedPage(
                    index=0,
                    text="распознанный текст страницы, достаточно длинный для приёмки",
                    confidence=0.42,
                ),
            )
        ),
    )

    await harness.run()

    assert harness.writer.documents == []
    cached = next(iter(harness.cache.records.values()))
    assert cached.status == REJECTED
    assert cached.reason == "low_confidence"
    assert harness.audit.names() == ["document_rejected"]
    assert harness.audit.events[0][1]["profile"] == "test"


async def test_metadata_outside_the_contract_fails_the_job_before_indexing() -> None:
    harness = ExtractJob()
    blob_id = await harness.blobs.put(DIGITAL, filename="f.pdf", media_type="application/pdf")
    bad = {"id": "hr/uploaded", "title": "Регламент"}

    with pytest.raises(Exception, match="upload"):
        await harness.job.run(
            {
                "blob_id": blob_id,
                "filename": "f.pdf",
                "media_type": "application/pdf",
                "metadata": bad,
            }
        )

    assert harness.writer.documents == []


async def test_a_missing_blob_is_a_payload_error() -> None:
    harness = ExtractJob()

    with pytest.raises(JobPayloadError, match="is gone"):
        await harness.job.run(
            {
                "blob_id": "0" * 64,
                "filename": "f.pdf",
                "media_type": "application/pdf",
                "metadata": METADATA,
            }
        )


@pytest.mark.parametrize("payload", [{}, {"blob_id": "x"}, {"blob_id": "x", "filename": "f"}])
async def test_an_incomplete_payload_is_rejected(payload: dict[str, object]) -> None:
    harness = ExtractJob()

    with pytest.raises(JobPayloadError):
        await harness.job.run(payload)


async def test_a_fixed_refusal_does_not_touch_the_corpus() -> None:
    """A refused document is a value, so the job completes with a recorded reason."""
    harness = ExtractJob()
    harness.extraction = FixedExtraction(document=await _refused_document())
    harness.job = DocumentExtractor(
        blobs=harness.blobs,
        extraction=harness.extraction,
        cache=harness.cache,
        writer=harness.writer,
        embedder=HashingEmbedder(dim=8),
        schema_path=SCHEMA,
        profile=harness.profile,
        audit=harness.audit,
    )

    await harness.run()

    assert harness.writer.documents == []
    assert next(iter(harness.cache.records.values())).reason == "encrypted"


async def _refused_document() -> object:
    return refused(RejectionReason.ENCRYPTED, engine="pdfium", content_hash="h", profile="test")
