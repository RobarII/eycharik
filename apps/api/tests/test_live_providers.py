"""Live providers, one tiny call each. Only runs under ``make test-live``.

This is the smoke test for the wiring, not for quality: it answers "do the key, the base URL, the
extra header, and the profile agree with each other" — the question that costs the most debugging
time when a model is swapped. Quality lives in ``make eval`` / ``make eval-retrieval``.

Every call is deliberately small: one short completion, two sentences to embed, two documents to
rerank. A run costs a fraction of a cent and proves the three provider legs independently.
"""

from __future__ import annotations

import httpx
import pytest

from onboarding.app.clock import SystemClock
from onboarding.app.llm.embeddings import build_embedder
from onboarding.app.llm.gateway import build_llm
from onboarding.app.llm.profiles import answer_profile
from onboarding.app.llm.rerank import build_reranker
from onboarding.app.settings import Settings
from onboarding.ports import CompletionRequest, Message

pytestmark = pytest.mark.eval


@pytest.fixture(scope="module")
def settings() -> Settings:
    resolved = Settings()
    if not resolved.llm_api_key.get_secret_value():
        pytest.skip("LLM_API_KEY is not set")
    return resolved


async def test_the_answer_model_answers_json(settings: Settings) -> None:
    async with httpx.AsyncClient(timeout=60.0) as client:
        llm = build_llm(settings, SystemClock(), client)
        completion = await llm.complete(
            CompletionRequest(
                messages=(Message(role="system", content='Верни JSON {"answer":"ok"}'),),
                response_format="json_object",
            )
        )

    assert completion.text.strip()
    assert completion.input_tokens > 0
    assert answer_profile(settings).model == completion.model or completion.model


async def test_the_embedder_returns_the_column_width(settings: Settings) -> None:
    async with httpx.AsyncClient(timeout=60.0) as client:
        embedder = build_embedder(settings, client, clock=SystemClock())
        vectors = await embedder.embed(["Отпуск без сохранения заработной платы", "Пропуск в офис"])

    assert len(vectors) == 2
    assert {len(vector) for vector in vectors} == {embedder.dim}


async def test_the_reranker_orders_by_relevance(settings: Settings) -> None:
    if not settings.rerank_model:
        pytest.skip("RERANK_MODEL is not set")
    async with httpx.AsyncClient(timeout=60.0) as client:
        reranker = build_reranker(settings, client, clock=SystemClock())
        order = await reranker.rerank(
            "отпуск без сохранения зарплаты",
            [
                "Как получить пропуск в офис.",
                "Отпуск без сохранения заработной платы оформляется заявлением.",
            ],
            top_n=2,
        )

    assert order
    assert order[0] == 1, f"the relevant document should rank first, got {order}"
