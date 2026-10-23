"""Indexing: corpus files in, embedded chunks out.

The pipeline is idempotent per document: replacing a document deletes its old chunks in the same
transaction, so a re-run after an edit never leaves two versions retrievable at once.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from onboarding.app.knowledge.ingest import load_corpus
from onboarding.core.chunking import split_document
from onboarding.ports import Embedder, KnowledgeDocumentRecord, KnowledgeWriter


@dataclass(frozen=True, slots=True)
class IngestReport:
    documents: int
    chunks: int


async def ingest(
    *,
    directory: Path,
    schema_path: Path,
    writer: KnowledgeWriter,
    embedder: Embedder,
    max_chars: int = 1200,
    overlap_chars: int = 200,
) -> IngestReport:
    loaded = load_corpus(directory, schema_path)
    chunks = 0
    for item in loaded:
        pieces = split_document(
            item.document, max_chars=max_chars, overlap_chars=overlap_chars
        )
        if not pieces:
            raise ValueError(f"{item.path}: document produced no chunks")
        embeddings = await embedder.embed([piece.text for piece in pieces])
        if len(embeddings) != len(pieces):
            raise ValueError(f"{item.path}: embedder returned a wrong number of vectors")
        await writer.replace_document(
            KnowledgeDocumentRecord(
                id=item.document.id,
                title=item.document.title,
                doc_type=item.doc_type,
                status=item.status,
                audience=item.document.audience,
                valid_from=item.document.valid_from,
                valid_to=item.document.valid_to,
                owner=item.document.owner,
                checksum=item.checksum,
            ),
            pieces,
            embeddings,
        )
        chunks += len(pieces)
    return IngestReport(documents=len(loaded), chunks=chunks)
