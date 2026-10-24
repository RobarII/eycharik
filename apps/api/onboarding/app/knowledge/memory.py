"""In-memory retrieval: the local and test backend.

It applies the same policy as the production path — ACL and validity first, then the lexical gate,
then fusion — so a ranking defect is visible without a database. The pieces that must not differ
(chunk window, embedding view, coverage floor, fusion weights, candidate budget) are read from
``core.retrieval.RetrievalPolicy``; the only backend-specific part left is the ordering function of
each retriever: token overlap here, ``ts_rank_cd`` in Postgres.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from onboarding.core.access import holds, predicates, subject_of
from onboarding.core.chunking import split_document
from onboarding.core.models import Chunk, Document, ScoredChunk
from onboarding.core.retrieval import RetrievalPolicy
from onboarding.ports import Embedder, SearchQuery

_TOKEN = re.compile(r"[a-zа-яё0-9]+")


@dataclass(frozen=True, slots=True)
class _IndexedChunk:
    chunk: Chunk
    document: Document
    vector: tuple[float, ...]
    tokens: frozenset[str]


class InMemoryKnowledgeBase:
    def __init__(
        self,
        entries: Sequence[_IndexedChunk],
        embedder: Embedder,
        *,
        policy: RetrievalPolicy | None = None,
    ) -> None:
        self._entries = tuple(entries)
        self._embedder = embedder
        self._policy = policy or RetrievalPolicy()

    @classmethod
    async def build(
        cls,
        documents: Sequence[Document],
        embedder: Embedder,
        *,
        policy: RetrievalPolicy | None = None,
    ) -> InMemoryKnowledgeBase:
        policy = policy or RetrievalPolicy()
        chunks: list[Chunk] = []
        owners: list[Document] = []
        for document in documents:
            chunks.extend(
                split_document(
                    document,
                    max_chars=policy.max_chars,
                    overlap_chars=policy.overlap_chars,
                )
            )
            owners.extend([document] * (len(chunks) - len(owners)))
        vectors = await embedder.embed([policy.embedding_view(chunk) for chunk in chunks])
        if len(vectors) != len(chunks):
            raise ValueError("embedder returned a wrong number of vectors")
        entries = [
            _IndexedChunk(
                chunk=chunk,
                document=document,
                vector=tuple(vector),
                tokens=_tokens(policy.lexical_view(chunk)),
            )
            for chunk, document, vector in zip(chunks, owners, vectors, strict=True)
        ]
        return cls(entries, embedder, policy=policy)

    async def search(self, query: SearchQuery) -> tuple[ScoredChunk, ...]:
        allowed = [
            entry
            for entry in self._entries
            if holds(
                predicates(query.audience, query.on_date),
                subject_of(entry.document),
            )
        ]
        if not allowed:
            return ()

        policy = self._policy
        query_tokens = _tokens(query.text)
        query_vector = (await self._embedder.embed([query.text]))[0]
        covered = {str(entry.chunk.id): len(entry.tokens & query_tokens) for entry in allowed}
        admitted = [
            entry
            for entry in allowed
            if policy.lexical_admits(covered[str(entry.chunk.id)], len(query_tokens))
        ]
        lexical = sorted(
            admitted,
            key=lambda entry: (-covered[str(entry.chunk.id)], str(entry.chunk.id)),
        )
        semantic = sorted(
            allowed,
            key=lambda entry: (-_cosine(entry.vector, query_vector), str(entry.chunk.id)),
        )
        fused = policy.fuse(
            [entry.chunk.id for entry in semantic[: policy.overfetch]],
            [entry.chunk.id for entry in lexical[: policy.overfetch]],
            limit=query.limit,
        )
        by_id = {entry.chunk.id: entry for entry in allowed}
        return tuple(
            ScoredChunk(chunk=by_id[chunk_id].chunk, score=score)
            for chunk_id, score in fused
            if chunk_id in by_id
        )


def _tokens(text: str) -> frozenset[str]:
    return frozenset(_TOKEN.findall(text.lower()))


def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right):
        raise ValueError("vectors have different dimensions")
    return sum(a * b for a, b in zip(left, right, strict=True))
