"""One model gateway: timeout, one retry, a circuit breaker, and cost accounting.

Every call in the application goes through this class. The model itself is a profile
(``apps/api/model-profiles/answer/<name>.yaml``): dialect, capabilities, envelope, and prices.
Providers are interchangeable behind it, so a model change is a profile change, not a code change.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

import httpx

from onboarding.app.llm.extractive import ExtractiveLLM
from onboarding.app.llm.profiles import answer_profile
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
    AnswerProfile,
    Clock,
    Completion,
    CompletionRequest,
    LLMUnavailableError,
)

RETRYABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504})
MAX_BACKOFF_S = 4.0


class LLMResponseError(RuntimeError):
    """The provider answered, but not with a completion we can use."""


class EmptyCompletionError(LLMResponseError):
    """A 200 with no content: often a reasoning model that spent its budget on thoughts."""


class GatewayLLM(LLM):
    def __init__(
        self,
        provider: Provider,
        profile: AnswerProfile,
        *,
        clock: Clock,
        client: httpx.AsyncClient,
        breaker: CircuitBreaker | None = None,
        max_retries: int | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._provider = provider
        self._profile = profile
        self._clock = clock
        self._client = client
        self._breaker = breaker or CircuitBreaker()
        self._max_retries = max(0, profile.max_retries if max_retries is None else max_retries)
        self._sleep = sleep

    @property
    def profile(self) -> AnswerProfile:
        return self._profile

    @property
    def breaker(self) -> CircuitBreaker:
        return self._breaker

    async def complete(self, request: CompletionRequest) -> Completion:
        now = self._clock.now()
        if not self._breaker.allows(now):
            raise LLMUnavailableError("circuit breaker is open")

        payload = self._payload(request)
        timeout = request.timeout_s if request.timeout_s is not None else self._profile.timeout_s
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
                    timeout=timeout,
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
            try:
                return self._parse(response, started)
            except EmptyCompletionError as error:
                last_error = str(error)
                if attempt < self._max_retries and self._profile.retry_empty_completion:
                    await self._backoff(attempt)
                    continue
                raise

        raise LLMUnavailableError(last_error)

    async def _backoff(self, attempt: int) -> None:
        if attempt < self._max_retries:
            await self._sleep(min(MAX_BACKOFF_S, 0.5 * (2**attempt)))

    def _payload(self, request: CompletionRequest) -> dict[str, object]:
        """Build the request from the profile's capabilities, not from assumptions about one API."""
        temperature = (
            request.temperature if request.temperature is not None else self._profile.temperature
        )
        max_tokens = (
            request.max_tokens if request.max_tokens is not None else self._profile.max_tokens
        )
        payload: dict[str, object] = {
            "model": self._profile.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": temperature,
            self._profile.max_tokens_field: max_tokens,
        }
        if self._profile.json_mode and request.response_format == "json_object":
            payload["response_format"] = {"type": "json_object"}
        if self._profile.reasoning_effort is not None:
            payload["reasoning_effort"] = self._profile.reasoning_effort
        return payload

    def _parse(self, response: httpx.Response, started: datetime) -> Completion:
        try:
            body = response.json()
            if not isinstance(body, dict):
                raise KeyError("response is not an object")
            outer_usage = body.get("usage")
            if "choices" not in body:
                # Some gateways (for example ClinePass) wrap the completion in
                # {"success": true, "data": {...}}. A failed envelope is not a completion.
                if body.get("success") is False:
                    raise LLMResponseError("provider reported an unsuccessful response")
                wrapped = body.get("data")
                if not isinstance(wrapped, dict):
                    raise KeyError("envelope has no data object")
                body = wrapped
            content = body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise LLMResponseError("provider response has no choices[0].message.content") from None
        if not isinstance(content, str) or not content.strip():
            raise EmptyCompletionError("provider returned empty content")

        usage = body.get("usage") or outer_usage or {}
        if not isinstance(usage, dict):
            usage = {}
        input_tokens = _int_or_zero(usage.get("prompt_tokens"))
        output_tokens = _int_or_zero(usage.get("completion_tokens"))
        cached_tokens = min(_cached_tokens(usage), input_tokens)
        latency_ms = int((self._clock.now() - started).total_seconds() * 1000)
        cost = (
            (input_tokens - cached_tokens) / 1000 * self._profile.price_input_rub_per_1k
            + cached_tokens / 1000 * self._profile.price_cache_read_rub_per_1k
            + output_tokens / 1000 * self._profile.price_output_rub_per_1k
        )
        return Completion(
            text=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_tokens,
            model=str(body.get("model") or self._profile.model),
            latency_ms=latency_ms,
            cost_rub=round(cost, 6),
        )


def _cached_tokens(usage: dict[str, object]) -> int:
    """OpenAI-compatible providers report the cached prefix here, or nowhere at all."""
    details = usage.get("prompt_tokens_details")
    if not isinstance(details, dict):
        return 0
    return _int_or_zero(details.get("cached_tokens"))


def _int_or_zero(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def build_llm(settings: Settings, clock: Clock, client: httpx.AsyncClient) -> LLM:
    if settings.llm_provider == "extractive":
        return ExtractiveLLM()
    profile = answer_profile(settings)
    provider: Provider
    if profile.family == "gigachat":
        provider = GigaChatProvider(
            base_url=settings.llm_base_url,
            auth_key=settings.llm_api_key,
            oauth_url=settings.llm_oauth_url,
        )
    else:
        provider = OpenAICompatibleProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            extra_headers=settings.llm_extra_headers,
        )
    return GatewayLLM(
        provider,
        profile,
        clock=clock,
        client=client,
        breaker=CircuitBreaker(
            threshold=settings.llm_breaker_threshold,
            cooldown=timedelta(seconds=settings.llm_breaker_cooldown_s),
        ),
        sleep=asyncio.sleep,
    )


__all__ = ["GatewayLLM", "LLMResponseError", "build_llm"]
