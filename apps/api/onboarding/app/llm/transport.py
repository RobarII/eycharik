"""One call envelope for every model: retry matrix, circuit breaker, and a single deadline.

The answer gateway and the sentiment classifier differ in what they send and in how they read the
answer. They must not differ in how an outage is handled, so the policy lives here once: a short
backoff, the breaker from ``core/breaker.py``, and one budget for the whole call. A dead endpoint
costs ``timeout_s`` in total, not ``timeout_s`` per attempt.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TypeVar

import httpx

from onboarding.app.llm.providers import PreparedRequest, ProviderError
from onboarding.app.settings import Settings
from onboarding.core.breaker import CircuitBreaker
from onboarding.ports import Clock

RETRYABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504})
MAX_BACKOFF_S = 4.0

T = TypeVar("T")


class TransportError(RuntimeError):
    """No usable answer within the budget: timeouts, retryable statuses, or an open breaker."""


class RejectedError(RuntimeError):
    """The endpoint answered with a status a retry cannot fix (a bad key, a bad model)."""

    def __init__(self, status_code: int) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


def model_breaker(settings: Settings) -> CircuitBreaker:
    """One outage policy for every model call: answers and classifiers trip the same way."""
    return CircuitBreaker(
        threshold=settings.llm_breaker_threshold,
        cooldown=timedelta(seconds=settings.llm_breaker_cooldown_s),
    )


@dataclass(slots=True)
class ModelTransport:
    """Per-provider HTTP state. One instance owns one breaker, so its failures are one signal."""

    client: httpx.AsyncClient
    clock: Clock
    breaker: CircuitBreaker = field(default_factory=CircuitBreaker)
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep

    async def call(
        self,
        *,
        prepare: Callable[[], Awaitable[PreparedRequest]],
        payload: dict[str, object],
        timeout_s: float,
        max_retries: int,
        parse: Callable[[httpx.Response, float], T],
        retry_parse: Callable[[Exception], bool] = lambda _error: False,
    ) -> T:
        """Send one payload, parse the answer, and retry what deserves a retry.

        ``parse`` sees the response and the seconds spent so far, so latency and cost accounting
        stay in the caller. A parse failure is retried only when ``retry_parse`` says so.
        """
        if timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        attempts = max(0, max_retries) + 1
        started = time.monotonic()
        deadline = started + timeout_s
        last = "no attempt"
        for attempt in range(attempts):
            now = self.clock.now()
            if not self.breaker.allows(now):
                raise TransportError("circuit breaker is open")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                prepared = await prepare()
                response = await self.client.post(
                    prepared.url,
                    headers=prepared.headers,
                    json=payload,
                    timeout=remaining,
                )
            except (httpx.TimeoutException, httpx.TransportError) as error:
                last = f"{type(error).__name__}: {error}"
                self.breaker = self.breaker.record_failure(now)
                await self._backoff(attempt, attempts, deadline)
                continue
            except ProviderError as error:
                last = str(error)
                self.breaker = self.breaker.record_failure(now)
                await self._backoff(attempt, attempts, deadline)
                continue

            if response.status_code in RETRYABLE_STATUS:
                last = f"HTTP {response.status_code}"
                self.breaker = self.breaker.record_failure(now)
                await self._backoff(attempt, attempts, deadline)
                continue
            if response.status_code >= 400:
                self.breaker = self.breaker.record_success()
                raise RejectedError(response.status_code)

            self.breaker = self.breaker.record_success()
            try:
                return parse(response, time.monotonic() - started)
            except Exception as error:
                if attempt + 1 < attempts and retry_parse(error):
                    last = str(error) or type(error).__name__
                    await self._backoff(attempt, attempts, deadline)
                    continue
                raise

        raise TransportError(last)

    async def _backoff(self, attempt: int, attempts: int, deadline: float) -> None:
        if attempt + 1 >= attempts:
            return
        left = deadline - time.monotonic()
        if left <= 0:
            return
        delay = min(MAX_BACKOFF_S, 0.5 * (2**attempt), left)
        if delay > 0:
            await self.sleep(delay)
