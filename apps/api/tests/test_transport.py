"""The shared model-call envelope: retries, the breaker, and one deadline for all attempts."""

from __future__ import annotations

import time
from collections.abc import Callable

import httpx
import pytest

from onboarding.app.clock import FrozenClock
from onboarding.app.llm.providers import PreparedRequest
from onboarding.app.llm.transport import (
    ModelTransport,
    RejectedError,
    TransportError,
)
from onboarding.core.breaker import CircuitBreaker

from .conftest import NOW

PREPARED = PreparedRequest(
    url="https://model.test/v1/call",
    headers={"Authorization": "Bearer k"},
    body={"state": "x"},
)


def handler_returning(
    *statuses: int,
) -> tuple[Callable[[httpx.Request], httpx.Response], list[httpx.Request]]:
    calls: list[httpx.Request] = []
    queue = list(statuses)

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(queue.pop(0) if len(queue) > 1 else queue[0], json={})

    return handler, calls


async def no_sleep(_: float) -> None:
    return None


def transport(
    handler: Callable[[httpx.Request], httpx.Response], **overrides: object
) -> ModelTransport:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    defaults: dict[str, object] = {"clock": FrozenClock(NOW), "sleep": no_sleep}
    return ModelTransport(client=client, **{**defaults, **overrides})  # type: ignore[arg-type]


async def send(
    transport: ModelTransport,
    *,
    timeout_s: float = 8.0,
    max_retries: int = 1,
    parse: Callable[[httpx.Response, float], object] | None = None,
    retry_parse: Callable[[Exception], bool] = lambda _error: False,
) -> object:
    return await transport.call(
        prepare=_prepared,
        timeout_s=timeout_s,
        max_retries=max_retries,
        parse=parse or (lambda response, _elapsed: response.status_code),
        retry_parse=retry_parse,
    )


async def _prepared() -> PreparedRequest:
    return PREPARED


async def test_retries_a_retryable_status_and_returns_the_parse() -> None:
    handler, calls = handler_returning(503, 200)

    result = await send(transport(handler))

    assert result == 200
    assert len(calls) == 2


async def test_a_client_error_is_not_retried() -> None:
    handler, calls = handler_returning(401)

    with pytest.raises(RejectedError) as raised:
        await send(transport(handler), max_retries=3)

    assert raised.value.status_code == 401
    assert len(calls) == 1


async def test_a_transport_error_is_retried_then_reported() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(TransportError, match="ReadTimeout"):
        await send(transport(handler), max_retries=1)

    assert calls == 2


async def test_an_open_breaker_costs_no_request() -> None:
    handler, calls = handler_returning(500)
    subject = transport(handler, breaker=CircuitBreaker(threshold=1))

    with pytest.raises(TransportError):
        await send(subject, max_retries=0)
    with pytest.raises(TransportError, match="breaker"):
        await send(subject, max_retries=0)

    assert len(calls) == 1


async def test_backoff_is_capped_by_the_remaining_budget() -> None:
    delays: list[float] = []

    async def record(delay: float) -> None:
        delays.append(delay)

    handler, _ = handler_returning(503)

    with pytest.raises(TransportError):
        await send(transport(handler, sleep=record), timeout_s=0.05, max_retries=3)

    assert delays
    assert all(delay <= 0.05 for delay in delays)


async def test_one_deadline_covers_every_attempt() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        time.sleep(0.03)
        return httpx.Response(503, json={})

    started = time.monotonic()

    with pytest.raises(TransportError):
        await send(transport(handler), timeout_s=0.08, max_retries=5)

    elapsed = time.monotonic() - started
    assert calls < 6
    assert elapsed < 0.5


async def test_parse_can_ask_for_a_retry() -> None:
    handler, calls = handler_returning(200)
    seen: list[int] = []

    def parse(response: httpx.Response, _elapsed: float) -> str:
        seen.append(response.status_code)
        if len(seen) == 1:
            raise ValueError("empty answer")
        return "ok"

    result = await send(
        transport(handler),
        max_retries=1,
        parse=parse,
        retry_parse=lambda error: isinstance(error, ValueError),
    )

    assert result == "ok"
    assert len(calls) == 2


async def test_parse_errors_that_do_not_ask_for_a_retry_are_raised() -> None:
    handler, calls = handler_returning(200)

    def parse(_response: httpx.Response, _elapsed: float) -> str:
        raise ValueError("malformed")

    with pytest.raises(ValueError, match="malformed"):
        await send(transport(handler), max_retries=2, parse=parse)

    assert len(calls) == 1
