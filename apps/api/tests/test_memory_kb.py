from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from onboarding.app.knowledge.embedding import HashingEmbedder
from onboarding.app.knowledge.ingest import load_corpus
from onboarding.app.knowledge.memory import InMemoryKnowledgeBase
from onboarding.ports import SearchQuery

ROOT = Path(__file__).resolve().parents[3]
KNOWLEDGE = ROOT / "knowledge"
SCHEMA = ROOT / "docs" / "contracts" / "doc.schema.json"


@pytest.fixture(scope="module")
async def kb() -> InMemoryKnowledgeBase:
    documents = [item.document for item in load_corpus(KNOWLEDGE, SCHEMA)]
    return await InMemoryKnowledgeBase.build(documents, HashingEmbedder(dim=512))


async def test_retrieves_the_leave_policy(kb: InMemoryKnowledgeBase) -> None:
    """A smoke test for the in-memory adapter, not a retrieval gate.

    The hashing embedder is a bag of tokens with no semantics, so the query carries the words the
    policy itself uses. Ranking quality belongs to ``make eval-retrieval`` on the real embedder;
    this test only proves the in-memory adapter returns what it indexed.
    """
    results = await kb.search(
        SearchQuery(
            text="ежегодный оплачиваемый отпуск",
            audience=("all",),
            on_date=date(2026, 5, 1),
        )
    )

    assert results
    assert results[0].chunk.doc_id == "hr/leave-policy"


async def test_retrieves_the_dms_policy(kb: InMemoryKnowledgeBase) -> None:
    results = await kb.search(
        SearchQuery(text="с какого дня действует ДМС", audience=("all",), on_date=date(2026, 5, 1))
    )

    assert results
    assert results[0].chunk.doc_id == "hr/benefits-dms"


async def test_retrieves_it_equipment(kb: InMemoryKnowledgeBase) -> None:
    results = await kb.search(
        SearchQuery(
            text="как получить ноутбук и доступы",
            audience=("all",),
            on_date=date(2026, 5, 1),
        )
    )

    assert results
    assert results[0].chunk.doc_id == "it/access-and-equipment"


async def test_hr_only_corpus_is_not_visible_without_the_scope(
    kb: InMemoryKnowledgeBase,
) -> None:
    results = await kb.search(
        SearchQuery(text="отпуск", audience=("all",), on_date=date(2026, 5, 1))
    )

    assert all(result.chunk.doc_id != "hr/secret" for result in results)


async def test_expired_documents_are_not_retrieved(kb: InMemoryKnowledgeBase) -> None:
    results = await kb.search(
        SearchQuery(text="отпуск", audience=("all",), on_date=date(2020, 1, 1))
    )

    assert results == ()


async def test_limit_is_respected(kb: InMemoryKnowledgeBase) -> None:
    results = await kb.search(
        SearchQuery(
            text="отпуск документы доступы ДМС",
            audience=("all",),
            on_date=date(2026, 5, 1),
            limit=2,
        )
    )

    assert len(results) <= 2
