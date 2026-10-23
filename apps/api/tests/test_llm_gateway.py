from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest
from pydantic import SecretStr

from onboarding.app.clock import FrozenClock
from onboarding.app.llm.gateway import GatewayLLM, LLMResponseError
from onboarding.app.llm.providers import GigaChatProvider, OpenAICompatibleProvider
from onboarding.core.breaker import CircuitBreaker
from onboarding.ports import CompletionRequest, LLMUnavailableError, Message

from .conftest import NOW

REQUEST = CompletionRequest(
    messages=(
        Message(role="system", content="Ты ассистент"),
        Message(role="user", content="Вопрос"),
    ),
    max_tokens=300,
    temperature=0.1,
)


def handler_returning(
    *bodies: tuple[int, dict[str, object]],
) -> tuple[Callable[[httpx.Request], httpx.Response], list[httpx.Request]]:
    calls: list[httpx.Request] = []
    queue = list(bodies)

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        status, body = queue.pop(0) if len(queue) > 1 else queue[0]
        return httpx.Response(status, json=body)

    return handler, calls


def completion_body(text: str = '{"answer": "ok"}') -> dict[str, object]:
    return {
        "model": "test-model",
        "choices": [{"message": {"content": text}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
    }


async def no_sleep(_: float) -> None:
    return None


def build(handler: Callable[[httpx.Request], httpx.Response], **overrides: object) -> GatewayLLM:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    defaults: dict[str, object] = {
        "clock": FrozenClock(NOW),
        "client": client,
        "max_retries": 1,
        "price_input_rub_per_1k": 0.1,
        "price_output_rub_per_1k": 0.2,
        "sleep": no_sleep,
    }
    return GatewayLLM(
        OpenAICompatibleProvider(base_url="https://llm.test/v1", api_key=SecretStr("sk-test")),
        "test-model",
        **{**defaults, **overrides},  # type: ignore[arg-type]
    )


async def test_returns_a_completion_and_counts_cost() -> None:
    handler, calls = handler_returning((200, completion_body()))
    gateway = build(handler)

    result = await gateway.complete(REQUEST)

    assert result.text == '{"answer": "ok"}'
    assert result.input_tokens == 100
    assert result.output_tokens == 50
    assert result.cost_rub == pytest.approx(100 / 1000 * 0.1 + 50 / 1000 * 0.2)
    assert len(calls) == 1
    body = json.loads(calls[0].content)
    assert body["model"] == "test-model"
    assert body["response_format"] == {"type": "json_object"}
    assert calls[0].headers["authorization"] == "Bearer sk-test"


async def test_retries_a_retryable_status() -> None:
    handler, calls = handler_returning((503, {}), (200, completion_body()))
    gateway = build(handler, max_retries=1)

    result = await gateway.complete(REQUEST)

    assert result.text
    assert len(calls) == 2
    assert not gateway.breaker.is_open


async def test_client_error_is_not_retried() -> None:
    handler, calls = handler_returning((400, {"error": "bad"}))

    with pytest.raises(LLMResponseError, match="HTTP 400"):
        await build(handler).complete(REQUEST)

    assert len(calls) == 1


async def test_open_breaker_short_circuits() -> None:
    handler, calls = handler_returning((500, {}))
    gateway = build(handler, breaker=CircuitBreaker(threshold=1), max_retries=3)

    with pytest.raises(LLMUnavailableError):
        await gateway.complete(REQUEST)
    with pytest.raises(LLMUnavailableError):
        await gateway.complete(REQUEST)

    assert len(calls) == 1


async def test_timeout_becomes_unavailable() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("slow", request=request)

    gateway = build(handler, max_retries=1)

    with pytest.raises(LLMUnavailableError, match="ReadTimeout"):
        await gateway.complete(REQUEST)
    assert calls == 2


async def test_malformed_response_is_reported() -> None:
    handler, _ = handler_returning((200, {"choices": []}))

    with pytest.raises(LLMResponseError, match="choices"):
        await build(handler).complete(REQUEST)


async def test_gigachat_refreshes_the_token_once() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.host == "oauth.test":
            return httpx.Response(
                200,
                json={"access_token": "gc-token", "expires_at": 9_999_999_999_000},
            )
        return httpx.Response(200, json=completion_body())

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = GigaChatProvider(
        base_url="https://gigachat.test/api/v1",
        auth_key=SecretStr("basic-key"),
        oauth_url="https://oauth.test/token",
    )
    gateway = GatewayLLM(
        provider,
        "GigaChat-2-Pro",
        clock=FrozenClock(NOW),
        client=client,
        sleep=no_sleep,
    )

    await gateway.complete(REQUEST)
    await gateway.complete(REQUEST)

    oauth_calls = [request for request in calls if request.url.host == "oauth.test"]
    chat_calls = [request for request in calls if request.url.host == "gigachat.test"]
    assert len(oauth_calls) == 1
    assert len(chat_calls) == 2
    assert chat_calls[0].headers["authorization"] == "Bearer gc-token"
