"""The rerank scope exists to catch a stage that never ran.

``--retrieval-only`` calls the knowledge base directly, so a reranker wired into the answer path
never sees the golden set and two runs look identical whether the model works or not. These tests
hold the scope to that difference: a reranker that reorders must move the metric, one that raises
must be counted as a failure and leave the fused order standing.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

import pytest

from onboarding.core.models import Chunk, ChunkId, DocId, ScoredChunk
from onboarding.evals.rerank import CaseDelta, deltas, measure
from onboarding.evals.runner import Case
from tests.fakes import FakeKnowledgeBase


@dataclass
class FixedReranker:
    """Returns the candidate indices in a declared order, so the test, not the model, ranks."""

    order: tuple[int, ...] = ()
    calls: list[tuple[str, tuple[str, ...], int]] = field(default_factory=list)

    async def rerank(
        self, query: str, documents: tuple[str, ...], *, top_n: int
    ) -> tuple[int, ...]:
        self.calls.append((query, documents, top_n))
        return self.order


@dataclass
class BrokenReranker:
    async def rerank(
        self, query: str, documents: tuple[str, ...], *, top_n: int
    ) -> tuple[int, ...]:
        raise RuntimeError("rerank is down")


def scored(doc_id: str, *, score: float = 0.5) -> ScoredChunk:
    chunk = Chunk(id=ChunkId(f"{doc_id}#0"), doc_id=DocId(doc_id), index=0, text=f"text {doc_id}")
    return ScoredChunk(chunk=chunk, score=score)


def case(expect_docs: tuple[str, ...] = ("hr/leave",)) -> Case:
    return Case(
        id="leave-days",
        question="Сколько дней отпуска?",
        audience="all",
        expect_docs=expect_docs,
        expect_contains=(),
        expect_escalation=False,
        expect_reason="",
    )


def ticks(values: tuple[float, ...] = (0.0, 0.25)) -> Callable[[], float]:
    """A clock that yields declared timestamps: latency is asserted, not measured."""
    iterator = iter(values)
    return lambda: next(iterator)


async def test_a_reranker_that_reorders_moves_the_metric() -> None:
    knowledge = FakeKnowledgeBase(chunks=(scored("other"), scored("hr/leave")))
    records = await measure(
        (case(),),
        knowledge=knowledge,
        reranker=FixedReranker(order=(1, 0)),
        recall_limit=30,
        rerank_limit=5,
        on_date=date(2026, 10, 24),
        clock=ticks(),
    )

    assert records[0].before_docs == ("other", "hr/leave")
    assert records[0].after_docs == ("hr/leave", "other")
    assert records[0].before_rr == pytest.approx(0.5)
    assert records[0].after_rr == pytest.approx(1.0)
    assert records[0].before_recall == pytest.approx(1.0)
    assert records[0].latency_ms == pytest.approx(250.0)
    assert records[0].reordered is True


async def test_a_broken_reranker_keeps_the_fused_order_and_is_counted() -> None:
    knowledge = FakeKnowledgeBase(chunks=(scored("other"), scored("hr/leave")))
    records = await measure(
        (case(),),
        knowledge=knowledge,
        reranker=BrokenReranker(),
        recall_limit=30,
        rerank_limit=5,
        on_date=date(2026, 10, 24),
    )

    delta = deltas(records)
    assert delta.failures == 1
    assert records[0].after_docs == records[0].before_docs
    assert delta.after_mrr == pytest.approx(delta.before_mrr)


async def test_the_window_is_the_reranker_limit_not_the_recall_limit() -> None:
    """A longer candidate list must not win by length: both orders are compared at ``top_n``."""
    knowledge = FakeKnowledgeBase(
        chunks=(scored("a"), scored("b"), scored("c"), scored("hr/leave"))
    )
    records = await measure(
        (case(),),
        knowledge=knowledge,
        reranker=FixedReranker(order=(2, 1)),
        recall_limit=30,
        rerank_limit=2,
        on_date=date(2026, 10, 24),
        clock=ticks(),
    )

    assert records[0].before_docs == ("a", "b")
    assert records[0].after_docs == ("c", "b")
    assert records[0].before_recall == 0.0
    assert records[0].after_recall == 0.0


async def test_a_single_candidate_skips_the_reranker() -> None:
    """One candidate cannot be reordered, so the call would only add latency."""
    reranker = FixedReranker(order=(0,))
    knowledge = FakeKnowledgeBase(chunks=(scored("hr/leave"),))
    records = await measure(
        (case(),),
        knowledge=knowledge,
        reranker=reranker,
        recall_limit=30,
        rerank_limit=5,
        on_date=date(2026, 10, 24),
    )

    assert reranker.calls == []
    assert records[0].after_rr == pytest.approx(1.0)


def test_deltas_drop_failures_from_quality_and_count_them() -> None:
    records = (
        CaseDelta("a", ("x",), ("x",), 1.0, 1.0, 1.0, 1.0, latency_ms=10.0),
        CaseDelta("b", ("x",), ("x",), 1.0, 1.0, 1.0, 1.0, latency_ms=30.0),
        CaseDelta("c", ("x",), ("x",), 0.0, 0.0, 0.0, 0.0, error="TransportError: down"),
    )

    delta = deltas(records)
    assert delta.cases == 3
    assert delta.failures == 1
    assert delta.after_mrr == pytest.approx(1.0)
    assert delta.latency_p50_ms == pytest.approx(10.0)
    assert delta.latency_p95_ms == pytest.approx(30.0)
    assert delta.reordered == 0
