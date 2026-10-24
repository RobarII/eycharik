"""Postgres knowledge base: vector search, lexical search, reciprocal rank fusion.

ACL and validity are SQL predicates in both branches, so a forbidden chunk can never reach the
ranker or the prompt.
"""

from __future__ import annotations

import logging
import typing
from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, Select, Text, delete, func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from onboarding.app.db.models import EMBEDDING_DIM, ChunkRow, DocumentRow, IndexStateRow
from onboarding.app.db.predicates import acl_clause
from onboarding.app.db.session import Database
from onboarding.core.models import Chunk, ChunkId, DocId, ScoredChunk
from onboarding.core.ranking import reciprocal_rank_fusion
from onboarding.core.retrieval import RetrievalPolicy
from onboarding.ports import (
    Embedder,
    KnowledgeDocumentRecord,
    KnowledgeUnavailableError,
    SearchQuery,
)

log = logging.getLogger(__name__)


class PostgresKnowledgeBase:
    def __init__(
        self,
        database: Database,
        embedder: Embedder,
        *,
        policy: RetrievalPolicy | None = None,
        bm25: bool = False,
    ) -> None:
        self._database = database
        self._embedder = embedder
        self._policy = policy or RetrievalPolicy()
        # An experiment switch, not a feature flag: ADR 0012 keeps BM25 out of the request path
        # until a measurement on a larger corpus says otherwise.
        self._bm25_enabled = bm25
        self._bm25_available: bool | None = None
        self._index_checked = False

    async def search(self, query: SearchQuery) -> tuple[ScoredChunk, ...]:
        if not query.text.strip():
            return ()
        try:
            vector = list((await self._embedder.embed((query.text,)))[0])
        except Exception as error:
            raise KnowledgeUnavailableError(f"embedding failed: {error}") from error
        async with self._database.session() as session:
            await self._check_index(session)
            if self._bm25_enabled and self._bm25_available is None:
                self._bm25_available = await _has_bm25(session)
                if not self._bm25_available:
                    # Enabled but unavailable is a configuration mistake, not a runtime failure:
                    # the two-list fusion is still correct, so the turn must not fail.
                    log.warning("bm25_enabled_but_pg_search_is_missing")
            policy = self._policy
            semantic = await _semantic_ids(session, query, vector, policy.overfetch)
            lexical = await _lexical_ids(session, query, policy, policy.overfetch)
            rankings = [semantic, lexical]
            weights = [1.0, policy.lexical_weight]
            if self._bm25_enabled and self._bm25_available:
                rankings.append(await _bm25_ids(session, query, policy.overfetch))
                weights.append(1.0)
            fused = reciprocal_rank_fusion(rankings, weights=weights, limit=query.limit)
            if not fused:
                return ()
            rows = {
                row.id: row
                for row in await session.scalars(
                    select(ChunkRow).where(ChunkRow.id.in_([cid for cid, _ in fused]))
                )
            }
        return tuple(
            ScoredChunk(chunk=_chunk(rows[chunk_id]), score=score)
            for chunk_id, score in fused
            if chunk_id in rows
        )

    async def _check_index(self, session: AsyncSession) -> None:
        """Refuse to search vectors that another model produced.

        The first search pays for one row read; later searches on the same instance are free. A
        table without a row is a pre-0012 index and is accepted as-is, because failing there would
        break every existing deployment on upgrade.
        """
        if self._index_checked:
            return
        self._index_checked = True
        state = await session.get(IndexStateRow, "active")
        if state is None:
            return
        current = getattr(self._embedder, "fingerprint", "")
        if current and state.embedder != current:
            raise KnowledgeUnavailableError(
                f"knowledge index was built with {state.embedder!r}, this process embeds with "
                f"{current!r}; reindex before serving answers"
            )
        # An embedder without a fingerprint still has a width, and the column is the only witness
        # left. Checking it here is what makes writing it worth a column at all.
        width = getattr(self._embedder, "dim", 0)
        if not current and width and state.dim != width:
            raise KnowledgeUnavailableError(
                f"knowledge index is {state.dim} wide, this process embeds {width}; "
                "reindex before serving answers"
            )


class PostgresKnowledgeWriter:
    def __init__(self, database: Database, embedder: object | None = None) -> None:
        self._database = database
        self._fingerprint = getattr(embedder, "fingerprint", "")
        self._dim = getattr(embedder, "dim", 0)

    async def replace_document(
        self,
        record: KnowledgeDocumentRecord,
        chunks: tuple[Chunk, ...],
        embeddings: tuple[tuple[float, ...], ...],
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        async with self._database.session() as session:
            await session.execute(
                insert(DocumentRow)
                .values(
                    id=str(record.id),
                    title=record.title,
                    type=record.doc_type,
                    status=record.status,
                    owner=record.owner,
                    audience=list(record.audience),
                    valid_from=record.valid_from,
                    valid_to=record.valid_to,
                    checksum=record.checksum,
                    body=record.body,
                    updated_at=func.now(),
                )
                .on_conflict_do_update(
                    index_elements=[DocumentRow.id],
                    set_={
                        "title": record.title,
                        "type": record.doc_type,
                        "status": record.status,
                        "owner": record.owner,
                        "audience": list(record.audience),
                        "valid_from": record.valid_from,
                        "valid_to": record.valid_to,
                        "checksum": record.checksum,
                        "body": record.body,
                        "updated_at": func.now(),
                    },
                )
            )
            if self._fingerprint:
                await session.execute(
                    insert(IndexStateRow)
                    .values(id="active", embedder=self._fingerprint, dim=self._dim, chunks=0)
                    .on_conflict_do_update(
                        index_elements=[IndexStateRow.id],
                        set_={"embedder": self._fingerprint, "dim": self._dim},
                    )
                )
            await session.execute(delete(ChunkRow).where(ChunkRow.doc_id == str(record.id)))
            for chunk, embedding in zip(chunks, embeddings, strict=True):
                await session.execute(
                    insert(ChunkRow).values(
                        id=str(chunk.id),
                        doc_id=str(chunk.doc_id),
                        index=chunk.index,
                        text=chunk.text,
                        context=chunk.context,
                        embedding=list(embedding),
                        ts=func.to_tsvector("russian", chunk.embedding_text),
                    )
                )


async def _semantic_ids(
    session: AsyncSession,
    query: SearchQuery,
    vector: Sequence[float],
    limit: int,
) -> tuple[ChunkId, ...]:
    rows = await session.scalars(
        _filtered(query)
        .with_only_columns(ChunkRow.id)
        # The id breaks equidistant ties, so a repeated run over one index returns one order. The
        # embedder itself is not deterministic, which is measured, not fixed here.
        .order_by(ChunkRow.embedding.cosine_distance(list(vector)), ChunkRow.id)
        .limit(limit)
    )
    return tuple(ChunkId(row) for row in rows)


async def _has_bm25(session: AsyncSession) -> bool:
    """ParadeDB is optional; a plain-Postgres deployment keeps the two-list fusion."""
    found = await session.scalar(
        text("SELECT count(*) FROM pg_extension WHERE extname = 'pg_search'")
    )
    return bool(found)


async def _bm25_ids(session: AsyncSession, query: SearchQuery, limit: int) -> tuple[ChunkId, ...]:
    score = func.pdb.score(ChunkRow.id).label("score")
    rows = await session.execute(
        _filtered(query)
        .with_only_columns(ChunkRow.id, score)
        .where(ChunkRow.text.op("@@@")(query.text))
        .order_by(score.desc())
        .limit(limit)
    )
    return tuple(ChunkId(row.id) for row in rows)


def _lexical_query(text: str) -> ColumnElement[Any]:
    """One tsquery per question, with the lexemes joined by OR.

    ``plainto_tsquery`` joins every lexeme with AND, and that is fatal for questions: «Сколько
    дней отпуска положено в первый год?» became ``'скольк' & 'дне' & 'отпуск' & 'полож' &
    'перв' & 'год'``, which no chunk satisfies. Measured on the golden set against the shipped
    corpus, the AND form returned an empty list for 112 of 137 questions, so the fusion ranked on
    the vector list alone and the lexical half of ADR 0003 did not exist in production.

    The union keeps the candidates and ``ts_rank_cd`` still orders them by coverage and proximity.
    Its tiebreak is the chunk id, so a repeated query over one index returns one order.
    """
    terms = func.plainto_tsquery("russian", text)
    return func.to_tsquery("russian", func.replace(terms.cast(Text), "&", "|"))


def _coverage(text: str) -> ColumnElement[int]:
    """How many of the question's lexemes a chunk contains.

    The OR query alone is too loose: a chunk that happens to contain «сколько» matches, and that
    is how a lexical list makes the fused order worse instead of better. Measured at the fusion
    level on the golden set (identical semantic lists, only the lexical list changing), an
    ungated OR list moved recall@5 0.993 -> 0.978 and MRR 0.864 -> 0.809 at equal weight. The
    gate asks a chunk to cover ``min(coverage_floor, n)`` question lexemes: three is enough
    evidence that the match is about the question and not about one stopword, and a two-word
    question («условия ДМС») must cover both words, because with fewer the gate would pass on
    anything. The floor itself belongs to ``core.retrieval``: the in-memory backend applies the
    same one, and a gate that exists twice is a gate that disagrees with itself.
    """
    question = func.tsvector_to_array(func.to_tsvector("russian", text))
    word = func.unnest(func.tsvector_to_array(ChunkRow.ts)).column_valued("word")
    matches = select(func.count()).where(word == func.any_(question))
    return typing.cast("ColumnElement[int]", matches.scalar_subquery())


async def _lexical_ids(
    session: AsyncSession,
    query: SearchQuery,
    policy: RetrievalPolicy,
    limit: int,
) -> tuple[ChunkId, ...]:
    ts_query = _lexical_query(query.text)
    rank = func.ts_rank_cd(ChunkRow.ts, ts_query)
    required = func.least(
        policy.coverage_floor,
        func.cardinality(func.tsvector_to_array(func.to_tsvector("russian", query.text))),
    )
    rows = await session.scalars(
        _filtered(query)
        .with_only_columns(ChunkRow.id)
        .where(ChunkRow.ts.op("@@")(ts_query), _coverage(query.text) >= required)
        .order_by(rank.desc(), ChunkRow.id)
        .limit(limit)
    )
    return tuple(ChunkId(row) for row in rows)


def _filters(query: SearchQuery) -> tuple[ColumnElement[bool], ...]:
    """The filter is one clause built from the one rule, not a second copy of it."""
    return (acl_clause(query.audience, query.on_date),)


def _filtered(query: SearchQuery) -> Select[ChunkRow]:
    return (
        select(ChunkRow)
        .join(DocumentRow, DocumentRow.id == ChunkRow.doc_id)
        .where(*_filters(query))
    )


def _chunk(row: ChunkRow) -> Chunk:
    return Chunk(
        id=ChunkId(row.id),
        doc_id=DocId(row.doc_id),
        index=row.index,
        text=row.text,
        context=row.context or "",
    )


def assert_embedding_width(dim: int) -> None:
    if dim != EMBEDDING_DIM:
        raise ValueError(
            f"EMBED_DIM is {dim}, but the kb_chunks.embedding column is vector({EMBEDDING_DIM}); "
            "changing it requires a migration"
        )
