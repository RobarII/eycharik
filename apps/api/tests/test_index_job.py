"""The markdown job indexes once and treats a cached result as done."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from onboarding.app.worker.index import DocumentIndexer
from onboarding.ports import ExtractionRecord

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "docs" / "contracts" / "doc.schema.json"
DOC = """---
id: hr/cached
title: Кэшированный документ
type: knowledge
status: active
owner: hr
audience: [all]
valid_from: 2026-01-01
---

## Раздел

Достаточно текста, чтобы документ стал одним фрагментом.
"""


class Blobs:
    async def put(self, content: bytes, *, filename: str, media_type: str) -> str:
        raise AssertionError("the indexer never writes")

    async def read(self, blob_id: str) -> bytes | None:
        return DOC.encode()


class Cache:
    def __init__(self) -> None:
        self.saved: list[ExtractionRecord] = []
        self.record: ExtractionRecord | None = None

    async def load(self, content_hash: str, profile_hash: str) -> ExtractionRecord | None:
        return self.record

    async def load_latest(self, content_hash: str) -> ExtractionRecord | None:
        return self.record

    async def save(self, record: ExtractionRecord) -> None:
        self.saved.append(record)
        self.record = record


class Writer:
    def __init__(self) -> None:
        self.calls = 0

    async def replace_document(self, *args: Any) -> None:
        self.calls += 1


class Embedder:
    dim = 2

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


class Audit:
    def __init__(self) -> None:
        self.events: list[str] = []

    async def record(self, name: str, **fields: object) -> None:
        self.events.append(name)


def build() -> tuple[DocumentIndexer, Cache, Writer, Audit]:
    cache, writer, audit = Cache(), Writer(), Audit()
    return (
        DocumentIndexer(
            blobs=Blobs(),  # type: ignore[arg-type]
            cache=cache,  # type: ignore[arg-type]
            writer=writer,  # type: ignore[arg-type]
            embedder=Embedder(),  # type: ignore[arg-type]
            schema_path=SCHEMA,
            audit=audit,  # type: ignore[arg-type]
        ),
        cache,
        writer,
        audit,
    )


async def test_the_job_indexes_a_markdown_blob() -> None:
    indexer, cache, writer, audit = build()

    await indexer.run({"blob_id": "abc"})

    assert writer.calls == 1
    assert cache.saved[0].status == "indexed"
    assert cache.saved[0].document_id == "hr/cached"
    assert audit.events == ["document_indexed"]


async def test_a_cached_result_is_not_indexed_twice() -> None:
    indexer, cache, writer, audit = build()
    cache.record = ExtractionRecord(
        content_hash="abc",
        profile_hash="markdown:v1",
        status="indexed",
        reason=None,
        engine="markdown",
        route="text",
        pages=0,
        min_confidence=1.0,
        document_id="hr/cached",
    )

    await indexer.run({"blob_id": "abc"})

    assert writer.calls == 0
    assert audit.events == ["document_index_cached"]


async def test_a_bad_document_is_cached_as_rejected() -> None:
    indexer, cache, writer, audit = build()
    content = b"# no frontmatter"

    class BadBlobs(Blobs):
        async def read(self, blob_id: str) -> bytes | None:
            return content

    indexer._blobs = BadBlobs()  # type: ignore[assignment]
    await indexer.run({"blob_id": "abc"})

    assert writer.calls == 0
    assert cache.saved[0].status == "rejected"
    assert cache.saved[0].reason == "invalid_document"
    assert audit.events == ["document_rejected"]
