"""One model gateway: timeout, one retry, a circuit breaker, and cost accounting.

Every call in the application goes through this class. Providers are interchangeable behind it, so
a provider incident is a configuration change, not a code change.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

import httpx

from onboarding.app.llm.extractive import ExtractiveLLM
from onboarding.app.llm.providers import (
    GigaChatProvider,
    OpenAICompatibleProvider,
    Provider,
    ProviderError,
)
from onboarding.app.settings import Settings
from onboarding.core.breaker import CircuitBreaker
from onboarding.ports import (
    LLM,
    Clock,
    Completion,
    CompletionRequest,
    LLMUnavailableError,
)

RETRYABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504})
MAX_BACKOFF_S = 4.0


class LLMResponseError(RuntimeError):
    """The provider answered, but not with a completion we can use."""


class GatewayLLM(LLM):
    def __init__(
        self,
        provider: Provider,
        model: str,
        *,
        clock: Clock,
        client: httpx.AsyncClient,
        breaker: CircuitBreaker | None = None,
        max_retries: int = 1,
        temperature: float = 0.2,
        price_input_rub_per_1k: float = 0.0,
        price_output_rub_per_1k: float = 0.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._provider = provider
        self._model = model
        self._clock = clock
        self._client = client
        self._breaker = breaker or CircuitBreaker()
        self._max_retries = max(0, max_retries)
        self._temperature = temperature
        self._price_in = price_input_rub_per_1k
        self._price_out = price_output_rub_per_1k
        self._sleep = sleep

    @property
    def breaker(self) -> CircuitBreaker:
        return self._breaker

    async def complete(self, request: CompletionRequest) -> Completion:
        now = self._clock.now()
        if not self._breaker.allows(now):
            raise LLMUnavailableError("circuit breaker is open")

        payload = self._payload(request)
        last_error: str = "no attempt"
        for attempt in range(self._max_retries + 1):
            if not self._breaker.allows(self._clock.now()):
                break
            started = self._clock.now()
            try:
                prepared = await self._provider.prepare(self._client)
                response = await self._client.post(
                    prepared.url,
                    headers=prepared.headers,
                    json=payload,
                    timeout=request.timeout_s,
                )
            except (httpx.TimeoutException, httpx.TransportError) as error:
                last_error = f"{type(error).__name__}: {error}"
                self._breaker = self._breaker.record_failure(now)
                await self._backoff(attempt)
                continue
            except ProviderError as error:
                last_error = str(error)
                self._breaker = self._breaker.record_failure(now)
                await self._backoff(attempt)
                continue

            if response.status_code in RETRYABLE_STATUS:
                last_error = f"HTTP {response.status_code}"
                self._breaker = self._breaker.record_failure(now)
                await self._backoff(attempt)
                continue
            if response.status_code >= 400:
                self._breaker = self._breaker.record_success()
                raise LLMResponseError(
                    f"provider rejected the request with HTTP {response.status_code}"
                )

            self._breaker = self._breaker.record_success()
            return self._parse(response, started)

        raise LLMUnavailableError(last_error)

    async def _backoff(self, attempt: int) -> None:
        if attempt < self._max_retries:
            await self._sleep(min(MAX_BACKOFF_S, 0.5 * (2**attempt)))

    def _payload(self, request: CompletionRequest) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.response_format == "json_object":
            payload["response_format"] = {"type": "json_object"}
        return payload

    def _parse(self, response: httpx.Response, started: datetime) -> Completion:
        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise LLMResponseError("provider response has no choices[0].message.content") from None
        if not isinstance(content, str) or not content.strip():
            raise LLMResponseError("provider returned empty content")

        usage = body.get("usage") or {}
        input_tokens = _int_or_zero(usage.get("prompt_tokens"))
        output_tokens = _int_or_zero(usage.get("completion_tokens"))
        latency_ms = int((self._clock.now() - started).total_seconds() * 1000)
        cost = (
            input_tokens / 1000 * self._price_in + output_tokens / 1000 * self._price_out
        )
        return Completion(
            text=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=str(body.get("model") or self._model),
            latency_ms=latency_ms,
            cost_rub=round(cost, 6),
        )


def _int_or_zero(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def build_llm(settings: Settings, clock: Clock, client: httpx.AsyncClient) -> LLM:
    if settings.llm_provider == "extractive":
        return ExtractiveLLM()
    provider: Provider
    if settings.llm_provider == "gigachat":
        provider = GigaChatProvider(
            base_url=settings.llm_base_url,
            auth_key=settings.llm_api_key,
            oauth_url=settings.llm_oauth_url,
        )
    else:
        provider = OpenAICompatibleProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
        )
    return GatewayLLM(
        provider,
        settings.llm_model,
        clock=clock,
        client=client,
        breaker=CircuitBreaker(
            threshold=settings.llm_breaker_threshold,
            cooldown=timedelta(seconds=settings.llm_breaker_cooldown_s),
        ),
        max_retries=settings.llm_max_retries,
        temperature=settings.llm_temperature,
        price_input_rub_per_1k=settings.llm_price_input_rub_per_1k,
        price_output_rub_per_1k=settings.llm_price_output_rub_per_1k,
    )


__all__ = ["GatewayLLM", "LLMResponseError", "build_llm"]
