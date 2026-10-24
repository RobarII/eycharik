"""In-memory retrieval: the local and test backend.

It applies the same order as the production path — ACL and validity first, then lexical and vector
ranking, then reciprocal rank fusion — so a ranking defect is visible without a database.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass

from onboarding.core.access import is_valid, permits
from onboarding.core.chunking import split_document
from onboarding.core.models import Chunk, Document, ScoredChunk
from onboarding.core.query import expand_query
from onboarding.core.ranking import reciprocal_rank_fusion
from onboarding.ports import Embedder, SearchQuery

_TOKEN = re.compile(r"[a-zа-яё0-9]+")


@dataclass(frozen=True, slots=True)
class _IndexedChunk:
    chunk: Chunk
    document: Document
    vector: tuple[float, ...]
    tokens: frozenset[str]


class InMemoryKnowledgeBase:
    def __init__(self, entries: Sequence[_IndexedChunk], embedder: Embedder) -> None:
        self._entries = tuple(entries)
        self._embedder = embedder

    @classmethod
    async def build(
        cls,
        documents: Sequence[Document],
        embedder: Embedder,
        *,
        max_chars: int = 1200,
        overlap_chars: int = 200,
    ) -> InMemoryKnowledgeBase:
        chunks: list[Chunk] = []
        owners: list[Document] = []
        for document in documents:
            for chunk in split_document(
                document, max_chars=max_chars, overlap_chars=overlap_chars
            ):
                chunks.append(chunk)
                owners.append(document)
        vectors = await embedder.embed([chunk.text for chunk in chunks])
        if len(vectors) != len(chunks):
            raise ValueError("embedder returned a wrong number of vectors")
        entries = [
            _IndexedChunk(
                chunk=chunk,
                document=document,
                vector=tuple(vector),
                tokens=_tokens(chunk.text),
            )
            for chunk, document, vector in zip(chunks, owners, vectors, strict=True)
        ]
        return cls(entries, embedder)

    async def search(self, query: SearchQuery) -> tuple[ScoredChunk, ...]:
        allowed = [
            entry
            for entry in self._entries
            if permits(entry.document.audience, query.audience)
            and is_valid(entry.document, query.on_date)
        ]
        if not allowed:
            return ()

        search_text = expand_query(query.text)
        query_tokens = _tokens(search_text)
        query_vector = (await self._embedder.embed([search_text]))[0]
        lexical = sorted(
            allowed,
            key=lambda entry: (-_overlap(entry.tokens, query_tokens), str(entry.chunk.id)),
        )
        semantic = sorted(
            allowed,
            key=lambda entry: (-_cosine(entry.vector, query_vector), str(entry.chunk.id)),
        )
        fused = reciprocal_rank_fusion(
            [
                [entry.chunk.id for entry in semantic[: query.limit]],
                [entry.chunk.id for entry in lexical[: query.limit]],
            ]
        )
        by_id = {entry.chunk.id: entry for entry in allowed}
        return tuple(
            ScoredChunk(chunk=by_id[chunk_id].chunk, score=score)
            for chunk_id, score in fused[: query.limit]
        )


def _tokens(text: str) -> frozenset[str]:
    return frozenset(_TOKEN.findall(text.lower()))


def _overlap(chunk_tokens: frozenset[str], query_tokens: frozenset[str]) -> float:
    if not query_tokens:
        return 0.0
    return len(chunk_tokens & query_tokens) / math.sqrt(len(chunk_tokens) + 1)


def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right):
        raise ValueError("vectors have different dimensions")
    return sum(a * b for a, b in zip(left, right, strict=True))
