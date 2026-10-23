"""Split a document into retrievable chunks with stable identifiers.

Chunk ids are ``doc_id#index``. Reindexing the same text produces the same ids, which is what makes
citations in stored answers meaningful after a corpus update.
"""

from __future__ import annotations

import re

from .models import Chunk, ChunkId, DocId, Document

DEFAULT_MAX_CHARS = 1200
DEFAULT_OVERLAP_CHARS = 200
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")


def split_document(
    document: Document,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> tuple[Chunk, ...]:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if not 0 <= overlap_chars < max_chars:
        raise ValueError("overlap_chars must be in [0, max_chars)")

    units = _units(document)
    if not units:
        return ()

    chunks: list[Chunk] = []
    buffer: list[str] = []
    size = 0

    def flush() -> None:
        nonlocal buffer, size
        text = "\n".join(buffer).strip()
        if text:
            index = len(chunks)
            chunks.append(
                Chunk(
                    id=ChunkId(f"{document.id}#{index}"),
                    doc_id=DocId(document.id),
                    index=index,
                    text=text,
                )
            )
        buffer = _tail(buffer, overlap_chars)
        size = sum(len(unit) + 1 for unit in buffer)

    for unit in units:
        if size + len(unit) > max_chars and buffer:
            flush()
        buffer.append(unit)
        size += len(unit) + 1

    if buffer:
        text = "\n".join(buffer).strip()
        if text and (not chunks or text != chunks[-1].text):
            index = len(chunks)
            chunks.append(
                Chunk(
                    id=ChunkId(f"{document.id}#{index}"),
                    doc_id=DocId(document.id),
                    index=index,
                    text=text,
                )
            )
    return tuple(chunks)


def _units(document: Document) -> list[str]:
    units: list[str] = []
    for raw_paragraph in _PARAGRAPH_BREAK.split(document.text):
        paragraph = raw_paragraph.strip()
        if not paragraph:
            continue
        for raw_sentence in _SENTENCE_BREAK.split(paragraph):
            sentence = raw_sentence.strip()
            if sentence:
                units.append(sentence)
    return units


def _tail(buffer: list[str], overlap_chars: int) -> list[str]:
    if overlap_chars == 0:
        return []
    kept: list[str] = []
    size = 0
    for unit in reversed(buffer):
        if size + len(unit) > overlap_chars and kept:
            break
        kept.append(unit)
        size += len(unit) + 1
    return list(reversed(kept))
