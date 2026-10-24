"""Rerank the retrieval candidates with one narrow HTTP call.

Retrieval is cheap and generous (``policy.overfetch``), the prompt is small (``rerank_limit``). A
cross-encoder sees the question and each candidate together, which is the first stage cannot do.
The adapter speaks the Cohere-shaped ``/rerank`` dialect that Cohere, Jina and OpenRouter share.

Failure is never fatal: a reranker outage keeps the hybrid order, which is exactly what the answer
pipeline used before this stage existed. The HTTP policy is the shared one from ``transport.py`` —
three attempts inside the stage budget, the same breaker, no private retry loop.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field

import httpx

from onboarding.app.clock import SystemClock
from onboarding.app.llm.profiles import rerank_profile
from onboarding.app.llm.providers import PreparedRequest
from onboarding.app.llm.transport import (
    ModelTransport,
    RejectedError,
    TransportError,
    model_breaker,
)
from onboarding.app.settings import Settings
from onboarding.core.breaker import CircuitBreaker
from onboarding.ports import Clock, RerankUnavailableError

MAX_DOCUMENTS = 100
MAX_ATTEMPTS = 3
# The free endpoint answers 429 in bursts, and a 0.5 s retry never clears one. Spaced attempts turn
# a burst into a slow rerank; the deadline stops the spending.
BACKOFF_S = (2.0, 6.0)


@dataclass(frozen=True, slots=True)
class RemoteReranker:
    client: httpx.AsyncClient
    base_url: str
    api_key: str
    model: str
    timeout_s: float = 3.0
    deadline_s: float = 6.0
    clock: Clock = field(default_factory=SystemClock, compare=False)
    breaker: CircuitBreaker = field(default_factory=CircuitBreaker, compare=False)
    monotonic: Callable[[], float] = field(default=time.monotonic, compare=False)
    sleep: Callable[[float], Awaitable[None]] = field(default=asyncio.sleep, compare=False)

    async def rerank(
        self, query: str, documents: Sequence[str], *, top_n: int
    ) -> tuple[int, ...]:
        if not documents:
            return ()
        if len(documents) > MAX_DOCUMENTS:
            raise RerankUnavailableError(f"at most {MAX_DOCUMENTS} documents per request")
        count = len(documents)

        def parse(response: httpx.Response, elapsed_s: float) -> tuple[int, ...]:
            del elapsed_s
            try:
                payload = response.json()
            except ValueError:
                raise RerankUnavailableError("rerank response is not JSON") from None
            return parse_rerank(payload, count=count, top_n=top_n)

        transport = ModelTransport(
            client=self.client,
            clock=self.clock,
            breaker=self.breaker,
            monotonic=self.monotonic,
            sleep=self.sleep,
            backoff_s=BACKOFF_S,
        )
        request = _RerankRequest(
            base_url=self.base_url,
            api_key=self.api_key,
            model=self.model,
            query=query,
            documents=tuple(documents),
            top_n=top_n,
        )
        try:
            return await transport.call(
                prepare=request.prepare,
                timeout_s=self.deadline_s,
                attempt_timeout_s=self.timeout_s,
                max_retries=MAX_ATTEMPTS - 1,
                parse=parse,
            )
        except RejectedError as error:
            raise RerankUnavailableError(
                f"rerank endpoint answered {error.status_code}"
            ) from None
        except TransportError as error:
            # The budget is what ran out, not the attempt count: name it, so a slow endpoint is
            # distinguishable in the audit from one that answers garbage.
            raise RerankUnavailableError(
                f"{error}; rerank deadline of {self.deadline_s}s spent"
            ) from None


@dataclass(frozen=True, slots=True)
class _RerankRequest:
    """One request, built once, so the transport can retry it without rebuilding the body."""

    base_url: str
    api_key: str
    model: str
    query: str
    documents: tuple[str, ...]
    top_n: int

    async def prepare(self) -> PreparedRequest:
        return PreparedRequest(
            url=f"{self.base_url.rstrip('/')}/rerank",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            body={
                "model": self.model,
                "query": self.query,
                "documents": list(self.documents),
                "top_n": min(self.top_n, len(self.documents)),
            },
        )


def build_reranker(
    settings: Settings, client: httpx.AsyncClient, *, clock: Clock
) -> RemoteReranker | None:
    """``None`` when no base URL is configured: the retrieval order is used as is."""
    profile = rerank_profile(settings)
    if profile is None:
        return None
    return RemoteReranker(
        client=client,
        base_url=settings.rerank_base_url,
        api_key=settings.rerank_api_key.get_secret_value(),
        model=profile.model,
        timeout_s=profile.timeout_s,
        deadline_s=profile.deadline_s,
        clock=clock,
        breaker=model_breaker(settings),
    )


def parse_rerank(payload: object, *, count: int, top_n: int) -> tuple[int, ...]:
    """Ordered, unique, in-range indices. Anything else is a provider bug, not a ranking."""
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list) or not results:
        raise RerankUnavailableError("rerank response has no results")
    ranked: list[tuple[float, int]] = []
    for item in results:
        if not isinstance(item, dict):
            raise RerankUnavailableError("rerank result is not an object")
        index = item.get("index")
        score = item.get("relevance_score")
        if isinstance(index, bool) or not isinstance(index, int):
            raise RerankUnavailableError("rerank result has no integer index")
        if not 0 <= index < count:
            raise RerankUnavailableError(f"rerank index {index} is out of range")
        if isinstance(score, bool) or not isinstance(score, int | float):
            raise RerankUnavailableError("rerank result has no numeric score")
        ranked.append((float(score), index))
    ordered = tuple(index for _, index in sorted(ranked, key=lambda pair: (-pair[0], pair[1])))
    if len(set(ordered)) != len(ordered):
        raise RerankUnavailableError("rerank returned a duplicate index")
    return ordered[:top_n]
