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
from onboarding.app.llm.profiles import embedding_profile
from onboarding.app.llm.providers import GigaChatProvider
from onboarding.app.settings import Settings
from onboarding.ports import KnowledgeUnavailableError

_BACKOFF = (0.5, 1.5, 3.0, 6.0, 10.0)


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
        dimensions_param: bool = False,
    ) -> None:
        self._client = client
        self._endpoint = endpoint
        self._authorization = authorization
        self._model = model
        self._dim = dim
        self._timeout = timeout_s
        self._dimensions_param = dimensions_param

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def fingerprint(self) -> str:
        """Model and width together: two models with the same width still produce two spaces."""
        return f"{self._model}@{self._dim}"

    async def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        if not texts:
            return ()
        response = await self._post_with_retry(list(texts))
        return parse_embeddings(response.json(), count=len(texts), dim=self._dim)

    def _body(self, texts: list[str]) -> dict[str, object]:
        body: dict[str, object] = {"model": self._model, "input": texts}
        if self._dimensions_param:
            body["dimensions"] = self._dim
        return body

    async def _post_with_retry(self, texts: list[str]) -> httpx.Response:
        """Gateways answer 429/503 under load; retries with a growing pause cover a cold shard.

        The pause used to be 0.2/0.4 s, shorter than a provider's own failover; a reindex or an eval
        run that dies on one 503 wastes far more than a few seconds of waiting.
        """
        last = "no attempt"
        for attempt in range(6):
            if attempt:
                await asyncio.sleep(_BACKOFF[attempt - 1])
            try:
                response = await self._client.post(
                    self._endpoint,
                    headers={
                        "Authorization": await self._authorization(),
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json=self._body(texts),
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
    """One embedder from one profile. The vector width is checked here, before any request."""
    profile = embedding_profile(settings)
    if profile.family == "local":
        return HashingEmbedder(dim=profile.dim)

    base_url = (settings.embed_base_url or settings.llm_base_url).rstrip("/")
    if profile.family == "gigachat":
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
            model=profile.model,
            dim=profile.dim,
            timeout_s=profile.timeout_s,
        )

    key = SecretStr(
        settings.embed_api_key.get_secret_value() or settings.llm_api_key.get_secret_value()
    )
    return RemoteEmbedder(
        client=client,
        endpoint=f"{base_url}/embeddings",
        authorization=_bearer(key),
        model=profile.model,
        dim=profile.dim,
        timeout_s=profile.timeout_s,
        dimensions_param=profile.dimensions_param,
    )


def _bearer(key: SecretStr) -> Callable[[], Awaitable[str]]:
    async def authorization() -> str:
        return f"Bearer {key.get_secret_value()}"

    return authorization


def parse_embeddings(payload: object, *, count: int, dim: int) -> tuple[tuple[float, ...], ...]:
    """Vectors in request order, or one typed failure.

    The same rule as ``parse_rerank``: a provider that answers something else is an outage, not a
    ``KeyError`` raised three frames inside the worker where the retry policy cannot see it. An
    index is required because the envelope promises one; a response without it is reordered by
    guess otherwise, and a silently permuted batch writes the wrong vector next to the wrong chunk.
    """
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list) or len(data) != count:
        raise KnowledgeUnavailableError("embedding response has a wrong number of vectors")
    ordered: dict[int, tuple[float, ...]] = {}
    for item in data:
        if not isinstance(item, dict):
            raise KnowledgeUnavailableError("embedding item is not an object")
        index = item.get("index")
        if isinstance(index, bool) or not isinstance(index, int):
            raise KnowledgeUnavailableError("embedding item has no integer index")
        if not 0 <= index < count:
            raise KnowledgeUnavailableError(f"embedding index {index} is out of range")
        raw = item.get("embedding")
        if not isinstance(raw, list) or len(raw) != dim:
            raise KnowledgeUnavailableError(
                f"expected {dim}-dimensional embeddings, got "
                f"{len(raw) if isinstance(raw, list) else 'none'}"
            )
        if any(isinstance(value, bool) or not isinstance(value, int | float) for value in raw):
            raise KnowledgeUnavailableError("embedding vector holds a non-numeric value")
        if index in ordered:
            raise KnowledgeUnavailableError(f"embedding index {index} is repeated")
        ordered[index] = tuple(float(value) for value in raw)
    return tuple(ordered[index] for index in sorted(ordered))
