from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace

import httpx
import pytest
from pydantic import SecretStr

from onboarding.app.clock import FrozenClock
from onboarding.app.llm.gateway import EmptyCompletionError, GatewayLLM, LLMResponseError
from onboarding.app.llm.providers import GigaChatProvider, OpenAICompatibleProvider
from onboarding.core.breaker import CircuitBreaker
from onboarding.ports import AnswerProfile, CompletionRequest, LLMUnavailableError, Message

from .conftest import NOW

REQUEST = CompletionRequest(
    messages=(
        Message(role="system", content="Ты ассистент"),
        Message(role="user", content="Вопрос"),
    ),
    max_tokens=300,
    temperature=0.1,
)

NO_ENVELOPE = CompletionRequest(
    messages=(Message(role="user", content="Вопрос"),),
)

PROFILE = AnswerProfile(
    name="test-model",
    model="test-model",
    max_retries=1,
    price_input_rub_per_1k=0.1,
    price_output_rub_per_1k=0.2,
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


def completion_body(
    text: str = '{"answer": "ok"}', *, cached_tokens: int = 0, finish_reason: str | None = None
) -> dict[str, object]:
    choice: dict[str, object] = {"message": {"content": text}}
    if finish_reason is not None:
        choice["finish_reason"] = finish_reason
    return _body(choice, cached_tokens)


def _body(choice: dict[str, object], cached_tokens: int) -> dict[str, object]:
    usage: dict[str, object] = {"prompt_tokens": 100, "completion_tokens": 50}
    if cached_tokens:
        usage["prompt_tokens_details"] = {"cached_tokens": cached_tokens}
    return {
        "model": "test-model",
        "choices": [choice],
        "usage": usage,
    }


async def no_sleep(_: float) -> None:
    return None


def build(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    profile: AnswerProfile = PROFILE,
    **overrides: object,
) -> GatewayLLM:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    defaults: dict[str, object] = {"clock": FrozenClock(NOW), "client": client, "sleep": no_sleep}
    return GatewayLLM(
        OpenAICompatibleProvider(base_url="https://llm.test/v1", api_key=SecretStr("sk-test")),
        profile,
        **{**defaults, **overrides},  # type: ignore[arg-type]
    )


async def test_counts_a_cached_prefix_at_its_own_price() -> None:
    """A provider that bills cache reads cheaper must not be charged full price for them."""
    profile = replace(PROFILE, price_cache_read_rub_per_1k=0.01)
    handler, _ = handler_returning((200, completion_body(cached_tokens=80)))
    gateway = build(handler, profile=profile)

    result = await gateway.complete(REQUEST)

    assert result.cached_input_tokens == 80
    expected = (20 / 1000 * 0.1) + (80 / 1000 * 0.01) + (50 / 1000 * 0.2)
    assert result.cost_rub == pytest.approx(expected)


async def test_a_cache_count_larger_than_the_prompt_is_clamped() -> None:
    profile = replace(PROFILE, price_cache_read_rub_per_1k=0.01)
    handler, _ = handler_returning((200, completion_body(cached_tokens=500)))
    gateway = build(handler, profile=profile)

    result = await gateway.complete(REQUEST)

    assert result.cached_input_tokens == 100


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


async def test_openai_provider_merges_extra_headers() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200)))
    provider = OpenAICompatibleProvider(
        base_url="https://llm.test/v1",
        api_key=SecretStr("sk-test"),
        extra_headers={"x-opencode-session": "onboarding"},
    )

    prepared = await provider.prepare(client, {"model": "m"})

    assert prepared.headers["x-opencode-session"] == "onboarding"
    assert prepared.headers["Authorization"] == "Bearer sk-test"


async def test_unwraps_a_gateway_response_envelope() -> None:
    handler, _ = handler_returning((200, {"success": True, "data": completion_body()}))
    gateway = build(handler)

    result = await gateway.complete(REQUEST)

    assert result.text == '{"answer": "ok"}'
    assert result.input_tokens == 100


async def test_rejects_an_unsuccessful_gateway_envelope() -> None:
    handler, _ = handler_returning((200, {"success": False, "data": completion_body()}))
    gateway = build(handler)

    with pytest.raises(LLMResponseError, match="unsuccessful"):
        await gateway.complete(REQUEST)


async def test_rejects_a_gateway_envelope_without_data() -> None:
    handler, _ = handler_returning((200, {"success": True, "data": None}))
    gateway = build(handler)

    with pytest.raises(LLMResponseError, match="choices"):
        await gateway.complete(REQUEST)


async def test_reads_envelope_level_usage() -> None:
    body = {
        "success": True,
        "usage": {"prompt_tokens": 7, "completion_tokens": 3},
        "data": {
            "model": "test-model",
            "choices": [{"message": {"content": '{"answer": "ok"}'}}],
        },
    }
    handler, _ = handler_returning((200, body))
    gateway = build(handler)

    result = await gateway.complete(REQUEST)

    assert result.input_tokens == 7
    assert result.output_tokens == 3


async def test_retries_a_retryable_status() -> None:
    handler, calls = handler_returning((503, {}), (200, completion_body()))
    gateway = build(handler)

    result = await gateway.complete(REQUEST)

    assert result.text
    assert len(calls) == 2
    assert not gateway.breaker.is_open


async def test_payload_follows_the_profile_capabilities() -> None:
    handler, calls = handler_returning((200, completion_body()))
    profile = AnswerProfile(
        name="reasoning",
        model="reasoning-model",
        json_mode=False,
        max_tokens_field="max_completion_tokens",
        reasoning_effort="low",
        temperature=0.7,
        max_tokens=99,
        timeout_s=4.0,
    )

    await build(handler, profile=profile).complete(NO_ENVELOPE)

    body = json.loads(calls[0].content)
    assert body["model"] == "reasoning-model"
    assert body["temperature"] == 0.7
    assert body["max_completion_tokens"] == 99
    assert body["reasoning_effort"] == "low"
    assert "response_format" not in body


async def test_request_envelope_overrides_the_profile() -> None:
    handler, calls = handler_returning((200, completion_body()))

    await build(handler).complete(REQUEST)

    body = json.loads(calls[0].content)
    assert body["temperature"] == 0.1
    assert body["max_tokens"] == 300


async def test_an_empty_completion_is_retried_by_default() -> None:
    handler, calls = handler_returning(
        (200, completion_body("")), (200, completion_body('{"answer": "ok"}'))
    )

    result = await build(handler).complete(REQUEST)

    assert result.text == '{"answer": "ok"}'
    assert len(calls) == 2


async def test_an_empty_completion_is_not_retried_when_the_profile_forbids_it() -> None:
    handler, calls = handler_returning((200, completion_body("")))
    profile = AnswerProfile(name="strict", model="strict-model", retry_empty_completion=False)

    with pytest.raises(EmptyCompletionError):
        await build(handler, profile=profile, max_retries=2).complete(REQUEST)

    assert len(calls) == 1


async def test_a_completion_cut_by_max_tokens_is_not_retried_as_empty() -> None:
    # The budget went to reasoning; one more attempt with the same budget repeats the wait.
    handler, calls = handler_returning((200, completion_body("", finish_reason="length")))

    with pytest.raises(LLMResponseError, match="max_tokens"):
        await build(handler).complete(REQUEST)

    assert len(calls) == 1


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
        PROFILE,
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


async def test_the_provider_reported_charge_reaches_the_completion() -> None:
    """OpenRouter reports ``usage.cost`` in USD; that number is the ledger, not a profile price."""
    body = completion_body()
    body["usage"]["cost"] = 0.0000055  # type: ignore[index]
    handler, _ = handler_returning((200, body))
    gateway = build(handler)

    result = await gateway.complete(REQUEST)

    assert result.reported_cost_usd == pytest.approx(0.0000055)


async def test_a_silent_provider_is_not_priced_at_zero() -> None:
    """``None`` means "not reported"; conflating it with zero invents a price nobody measured."""
    handler, _ = handler_returning((200, completion_body()))
    gateway = build(handler)

    result = await gateway.complete(REQUEST)

    assert result.reported_cost_usd is None
