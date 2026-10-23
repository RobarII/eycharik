"""Rerank the retrieval candidates with one narrow HTTP call.

Retrieval is cheap and generous (``recall_limit``), the prompt is small (``rerank_limit``). A
cross-encoder sees the question and each candidate together, which is the first stage cannot do.
The adapter speaks the Cohere-shaped ``/rerank`` dialect that Cohere, Jina and OpenRouter share.

Failure is never fatal: a reranker outage keeps the hybrid order, which is exactly what the answer
pipeline used before this stage existed.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass

import httpx

from onboarding.app.llm.profiles import rerank_profile
from onboarding.app.settings import Settings
from onboarding.ports import RerankUnavailableError

_BACKOFF = (2.0, 6.0)

MAX_DOCUMENTS = 100


@dataclass(frozen=True, slots=True)
class RemoteReranker:
    client: httpx.AsyncClient
    base_url: str
    api_key: str
    model: str
    timeout_s: float = 3.0

    async def rerank(
        self, query: str, documents: Sequence[str], *, top_n: int
    ) -> tuple[int, ...]:
        if not documents:
            return ()
        if len(documents) > MAX_DOCUMENTS:
            raise RerankUnavailableError(f"at most {MAX_DOCUMENTS} documents per request")
        response = await self._post_with_retry(query, documents, top_n)
        return parse_rerank(response.json(), count=len(documents), top_n=top_n)

    async def _post_with_retry(
        self, query: str, documents: Sequence[str], top_n: int
    ) -> httpx.Response:
        last = "no attempt"
        # The free endpoint answers 429 in bursts; a single 0.2 s retry never clears one. Three
        # spaced attempts turn a burst into a slow rerank instead of a silent fallback to the
        # fused order, which is what an eval would then measure by accident.
        for attempt in range(3):
            if attempt:
                await asyncio.sleep(_BACKOFF[attempt - 1])
            try:
                response = await self.client.post(
                    f"{self.base_url.rstrip('/')}/rerank",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={
                        "model": self.model,
                        "query": query,
                        "documents": list(documents),
                        "top_n": min(top_n, len(documents)),
                    },
                    timeout=self.timeout_s,
                )
            except httpx.HTTPError as error:
                last = f"rerank request failed: {error}"
                continue
            if response.status_code in {429, 500, 502, 503, 504}:
                last = f"rerank endpoint answered {response.status_code}"
                continue
            if response.status_code >= 400:
                raise RerankUnavailableError(f"rerank endpoint answered {response.status_code}")
            return response
        raise RerankUnavailableError(last)


def build_reranker(settings: Settings, client: httpx.AsyncClient) -> RemoteReranker | None:
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
