"""One model gateway: the answer call, its envelope, and its cost accounting.

Every chat call in the application goes through this class. The model itself is a profile
(``apps/api/model-profiles/answer/<name>.yaml``): dialect, capabilities, envelope, and prices.
Providers are interchangeable behind it, so a model change is a profile change, not a code change.
The retry policy and the breaker live in ``transport.py``, shared with every other model call.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import httpx

from onboarding.app.llm.extractive import ExtractiveLLM
from onboarding.app.llm.profiles import answer_profile
from onboarding.app.llm.providers import (
    GigaChatProvider,
    OpenAICompatibleProvider,
    Provider,
)
from onboarding.app.llm.transport import (
    ModelTransport,
    RejectedError,
    TransportError,
    model_breaker,
)
from onboarding.app.llm.usage import reported_cost_usd
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
        self._max_retries = max(0, profile.max_retries if max_retries is None else max_retries)
        self._transport = ModelTransport(
            client=client, clock=clock, breaker=breaker or CircuitBreaker(), sleep=sleep
        )

    @property
    def profile(self) -> AnswerProfile:
        return self._profile

    @property
    def breaker(self) -> CircuitBreaker:
        return self._transport.breaker

    async def complete(self, request: CompletionRequest) -> Completion:
        payload = self._payload(request)
        timeout = request.timeout_s if request.timeout_s is not None else self._profile.timeout_s
        try:
            return await self._transport.call(
                prepare=lambda: self._provider.prepare(self._transport.client),
                payload=payload,
                timeout_s=timeout,
                max_retries=self._max_retries,
                parse=self._parse,
                retry_parse=self._retry_empty,
            )
        except RejectedError as error:
            raise LLMResponseError(f"provider rejected the request with {error}") from None
        except TransportError as error:
            raise LLMUnavailableError(str(error)) from None

    def _retry_empty(self, error: Exception) -> bool:
        return isinstance(error, EmptyCompletionError) and self._profile.retry_empty_completion

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

    def _parse(self, response: httpx.Response, elapsed_s: float) -> Completion:
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
        return Completion(
            text=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_tokens,
            model=str(body.get("model") or self._profile.model),
            latency_ms=int(elapsed_s * 1000),
            cost_rub=round(self._cost(input_tokens, output_tokens, cached_tokens), 6),
            cost_usd=reported_cost_usd(usage),
        )

    def _cost(self, input_tokens: int, output_tokens: int, cached_tokens: int) -> float:
        return (
            (input_tokens - cached_tokens) / 1000 * self._profile.price_input_rub_per_1k
            + cached_tokens / 1000 * self._profile.price_cache_read_rub_per_1k
            + output_tokens / 1000 * self._profile.price_output_rub_per_1k
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
        breaker=model_breaker(settings),
        sleep=asyncio.sleep,
    )


__all__ = ["GatewayLLM", "LLMResponseError", "build_llm"]
