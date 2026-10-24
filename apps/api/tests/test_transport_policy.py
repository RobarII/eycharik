"""One outage policy, three adapters.

The answer gateway, the embedder and the reranker send different bodies to different endpoints. What
they must share is how a dead endpoint is treated: a bounded number of attempts inside one budget,
a backoff that grows, and a breaker that stops the fourth try before it opens a socket. These tests
parametrise over the three adapters, so a fourth adapter that brings its own retry loop has to fail
here rather than in production.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime

import httpx
import pytest
from pydantic import SecretStr

from onboarding.app.clock import FrozenClock
from onboarding.app.llm.embeddings import RemoteEmbedder
from onboarding.app.llm.gateway import GatewayLLM
from onboarding.app.llm.providers import OpenAICompatibleProvider
from onboarding.app.llm.rerank import RemoteReranker
from onboarding.core.breaker import CircuitBreaker
from onboarding.ports import (
    AnswerProfile,
    CompletionRequest,
    KnowledgeUnavailableError,
    LLMUnavailableError,
    Message,
    RerankUnavailableError,
)

from .conftest import NOW

PROFILE = AnswerProfile(name="test-model", model="test-model", max_retries=5)
REQUEST = CompletionRequest(messages=(Message(role="user", content="Вопрос"),))


async def _no_sleep(_seconds: float) -> None:
    return None


def open_breaker(now: datetime) -> CircuitBreaker:
    return CircuitBreaker(threshold=1, failures=1, opened_at=now)


def adapters(
    client: httpx.AsyncClient,
    *,
    breaker: CircuitBreaker,
    clock: datetime = NOW,
    sleep: Callable[[float], Awaitable[None]] = _no_sleep,
    embed_timeout_s: float = 1.0,
) -> list[tuple[str, Callable[[], Awaitable[object]], type[Exception]]]:
    """The three callers that share the transport, each with one call to make."""

    async def authorization() -> str:
        return "Bearer secret"

    embedder = RemoteEmbedder(
        client=client,
        endpoint="https://example.test/embeddings",
        authorization=authorization,
        model="model",
        dim=3,
        timeout_s=embed_timeout_s,
        clock=FrozenClock(clock),
        breaker=breaker,
        sleep=sleep,
    )
    reranker = RemoteReranker(
        client=client,
        base_url="https://example.test",
        api_key="secret",
        model="cohere/rerank-v3.5",
        clock=FrozenClock(clock),
        breaker=breaker,
        sleep=sleep,
    )
    gateway = GatewayLLM(
        OpenAICompatibleProvider(
            base_url="https://example.test/v1", api_key=SecretStr("sk-test")
        ),
        PROFILE,
        clock=FrozenClock(clock),
        client=client,
        breaker=breaker,
        sleep=sleep,
    )
    return [
        ("embeddings", lambda: embedder.embed(("а",)), KnowledgeUnavailableError),
        ("rerank", lambda: reranker.rerank("вопрос", ("один",), top_n=1), RerankUnavailableError),
        ("gateway", lambda: gateway.complete(REQUEST), LLMUnavailableError),
    ]


@pytest.mark.parametrize("index", [0, 1, 2])
async def test_every_adapter_opens_its_breaker_and_stops_calling(index: int) -> None:
    """A dead endpoint costs the threshold, not the retry budget."""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        name, call, expected = adapters(
            client, breaker=CircuitBreaker(threshold=2)
        )[index]
        with pytest.raises(expected):
            await call()

    assert len(calls) == 2, f"{name} kept calling after the breaker opened"


@pytest.mark.parametrize("index", [0, 1, 2])
async def test_an_open_breaker_makes_no_request_at_all(index: int) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        _, call, expected = adapters(client, breaker=open_breaker(NOW))[index]
        with pytest.raises(expected, match="circuit breaker is open"):
            await call()

    assert calls == []


async def test_a_success_resets_the_failure_count() -> None:
    """A 503 followed by a 200 leaves a breaker that has one more failure of room, not one fewer."""
    responses = [
        httpx.Response(503),
        httpx.Response(200, json={"data": [{"index": 0, "embedding": [1.0, 2.0, 3.0]}]}),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return responses.pop(0) if len(responses) > 1 else responses[0]

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        embedder = RemoteEmbedder(
            client=client,
            endpoint="https://example.test/embeddings",
            authorization=_token,
            model="model",
            dim=3,
            clock=FrozenClock(NOW),
            breaker=CircuitBreaker(threshold=3),
            sleep=_no_sleep,
        )

        vectors = await embedder.embed(("а",))

    assert vectors == ((1.0, 2.0, 3.0),)
    assert embedder.breaker.failures == 0
    assert not embedder.breaker.is_open


async def test_an_attempt_is_capped_below_the_whole_budget() -> None:
    """A rerank stage gets three seconds a try inside a six second budget, not six a try."""
    seen: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        timeouts = request.extensions.get("timeout", {})
        seen.append(float(timeouts.get("read", 0.0)))
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [1.0, 2.0, 3.0]}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        embedder = RemoteEmbedder(
            client=client,
            endpoint="https://example.test/embeddings",
            authorization=_token,
            model="model",
            dim=3,
            timeout_s=1.0,
            clock=FrozenClock(NOW),
            sleep=_no_sleep,
        )
        await embedder.embed(("а",))

    assert seen == [1.0]


async def _token() -> str:
    return "Bearer secret"
