"""The reranker adapter: a strict reader of one HTTP dialect, and a safe fallback."""

from __future__ import annotations

import httpx
import pytest

from onboarding.app.llm.rerank import RemoteReranker, parse_rerank
from onboarding.ports import RerankUnavailableError


def payload(*pairs: tuple[int, float]) -> dict[str, object]:
    return {
        "results": [
            {"index": index, "relevance_score": score, "document": {"text": "..."}}
            for index, score in pairs
        ]
    }


def test_orders_by_score_not_by_provider_order() -> None:
    order = parse_rerank(payload((0, 0.1), (1, 0.9), (2, 0.5)), count=3, top_n=3)

    assert order == (1, 2, 0)


def test_respects_top_n() -> None:
    order = parse_rerank(payload((0, 0.1), (1, 0.9), (2, 0.5)), count=3, top_n=2)

    assert order == (1, 2)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"results": []},
        payload((0, 0.5), (0, 0.4)),
        payload((3, 0.5)),
        {"results": [{"index": 0}]},
        {"results": [{"index": "0", "relevance_score": 0.5}]},
    ],
)
def test_rejects_a_broken_response(body: dict[str, object]) -> None:
    with pytest.raises(RerankUnavailableError):
        parse_rerank(body, count=3, top_n=3)


async def test_sends_the_cohere_shaped_request() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = request.read().decode()
        return httpx.Response(200, json=payload((1, 0.9), (0, 0.2)))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        reranker = RemoteReranker(
            client=client,
            base_url="https://example.test/api/v1",
            api_key="secret",
            model="cohere/rerank-v3.5",
        )
        order = await reranker.rerank("вопрос", ("первый", "второй"), top_n=1)

    assert order == (1,)
    assert seen["url"] == "https://example.test/api/v1/rerank"
    assert seen["auth"] == "Bearer secret"
    assert '"top_n":1' in str(seen["body"])


async def test_http_error_falls_back_loudly() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(503))
    async with httpx.AsyncClient(transport=transport) as client:
        reranker = RemoteReranker(
            client=client,
            base_url="https://example.test",
            api_key="secret",
            model="cohere/rerank-v3.5",
        )
        with pytest.raises(RerankUnavailableError):
            await reranker.rerank("вопрос", ("один",), top_n=1)


async def test_retries_once_when_the_gateway_is_busy() -> None:
    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) == 1:
            return httpx.Response(503)
        return httpx.Response(200, json=payload((0, 0.9)))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        reranker = RemoteReranker(
            client=client,
            base_url="https://example.test",
            api_key="secret",
            model="cohere/rerank-v3.5",
        )
        order = await reranker.rerank("вопрос", ("один",), top_n=1)

    assert order == (0,)
    assert len(attempts) == 2
