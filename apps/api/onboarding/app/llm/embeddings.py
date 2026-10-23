"""Embedding adapters.

Dimensions are validated against the database column before the first request, so a mismatched
model fails at startup instead of writing vectors that cannot be compared.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence

import httpx
from pydantic import SecretStr

from onboarding.app.knowledge.embedding import HashingEmbedder
from onboarding.app.llm.providers import GigaChatProvider
from onboarding.app.settings import Settings
from onboarding.ports import KnowledgeUnavailableError


class RemoteEmbedder:
    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        endpoint: str,
        authorization: Callable[[], Awaitable[str]],
        model: str,
        dim: int,
        timeout_s: float = 10.0,
    ) -> None:
        self._client = client
        self._endpoint = endpoint
        self._authorization = authorization
        self._model = model
        self._dim = dim
        self._timeout = timeout_s

    @property
    def dim(self) -> int:
        return self._dim

    async def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        if not texts:
            return ()
        response = await self._post_with_retry(list(texts))
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list) or len(data) != len(texts):
            raise KnowledgeUnavailableError("embedding response has a wrong number of vectors")
        vectors: list[tuple[float, ...]] = []
        for item in sorted(data, key=lambda entry: int(entry["index"])):
            raw = item.get("embedding")
            if not isinstance(raw, list) or len(raw) != self._dim:
                raise KnowledgeUnavailableError(
                    f"expected {self._dim}-dimensional embeddings, got "
                    f"{len(raw) if isinstance(raw, list) else 'none'}"
                )
            vectors.append(tuple(float(value) for value in raw))
        return tuple(vectors)

    async def _post_with_retry(self, texts: list[str]) -> httpx.Response:
        """Cheap gateways answer 429/503 under load; two retries turn an outage into a delay."""
        last = "no attempt"
        for attempt in range(3):
            if attempt:
                await asyncio.sleep(0.2 * attempt)
            try:
                response = await self._client.post(
                    self._endpoint,
                    headers={
                        "Authorization": await self._authorization(),
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={"model": self._model, "input": texts},
                    timeout=self._timeout,
                )
            except httpx.HTTPError as error:
                last = f"embedding request failed: {error}"
                continue
            if response.status_code in {429, 500, 502, 503, 504}:
                last = f"embedding endpoint answered {response.status_code}"
                continue
            if response.status_code >= 400:
                raise KnowledgeUnavailableError(
                    f"embedding endpoint answered {response.status_code}"
                )
            return response
        raise KnowledgeUnavailableError(last)


def build_embedder(
    settings: Settings, client: httpx.AsyncClient
) -> HashingEmbedder | RemoteEmbedder:
    if settings.embed_provider == "hashing":
        return HashingEmbedder(dim=settings.embed_dim)

    base_url = (settings.embed_base_url or settings.llm_base_url).rstrip("/")
    if settings.embed_provider == "gigachat":
        provider = GigaChatProvider(
            base_url=base_url,
            auth_key=settings.llm_api_key,
            oauth_url=settings.llm_oauth_url,
            scope=settings.llm_embed_scope,
        )
        return RemoteEmbedder(
            client=client,
            endpoint=f"{base_url}/embeddings",
            authorization=lambda: provider.authorization(client),
            model=settings.embed_model,
            dim=settings.embed_dim,
        )

    key = SecretStr(
        settings.embed_api_key.get_secret_value() or settings.llm_api_key.get_secret_value()
    )
    return RemoteEmbedder(
        client=client,
        endpoint=f"{base_url}/embeddings",
        authorization=_bearer(key),
        model=settings.embed_model,
        dim=settings.embed_dim,
    )


def _bearer(key: SecretStr) -> Callable[[], Awaitable[str]]:
    async def authorization() -> str:
        return f"Bearer {key.get_secret_value()}"

    return authorization
