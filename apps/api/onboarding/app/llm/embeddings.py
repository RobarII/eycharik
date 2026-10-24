"""Embedding adapters.

Dimensions are validated against the database column before the first request, so a mismatched
model fails at startup instead of writing vectors that cannot be compared.

The HTTP policy is not written here. ``ModelTransport`` owns the retry matrix, the backoff and the
breaker for every model call, so an embedder outage trips the same signal a chat outage does
instead of spending six attempts of its own on every reindex and every search.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence

import httpx
from pydantic import SecretStr

from onboarding.app.clock import SystemClock
from onboarding.app.knowledge.embedding import HashingEmbedder
from onboarding.app.llm.profiles import embedding_profile
from onboarding.app.llm.providers import GigaChatProvider, PreparedRequest
from onboarding.app.llm.transport import (
    ModelTransport,
    RejectedError,
    TransportError,
    model_breaker,
)
from onboarding.app.settings import Settings
from onboarding.core.breaker import CircuitBreaker
from onboarding.ports import Clock, KnowledgeUnavailableError

# Six attempts inside one budget: a cold shard answers 503 for a few seconds, and a reindex that
# dies on the first one wastes minutes. The budget bounds the whole call, not each attempt.
MAX_ATTEMPTS = 6
TOTAL_BUDGET_S = 45.0
# The pause grows: a cold shard answers 503 for a few seconds, and a reindex that gives up early
# wastes minutes of a rerun.
BACKOFF_S = (0.5, 1.5, 3.0, 6.0, 10.0)


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
        clock: Clock | None = None,
        breaker: CircuitBreaker | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        transport = ModelTransport(
            client=client,
            clock=clock or SystemClock(),
            breaker=breaker or CircuitBreaker(),
            backoff_s=BACKOFF_S,
        )
        if sleep is not None:
            transport.sleep = sleep
        self._transport = transport
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

    @property
    def breaker(self) -> CircuitBreaker:
        return self._transport.breaker

    async def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        if not texts:
            return ()
        expected = len(texts)

        def parse(response: httpx.Response, elapsed_s: float) -> tuple[tuple[float, ...], ...]:
            del elapsed_s
            return parse_embeddings(_json(response), count=expected, dim=self._dim)

        try:
            return await self._transport.call(
                prepare=lambda: self._prepare(list(texts)),
                timeout_s=TOTAL_BUDGET_S,
                attempt_timeout_s=self._timeout,
                max_retries=MAX_ATTEMPTS - 1,
                parse=parse,
            )
        except RejectedError as error:
            raise KnowledgeUnavailableError(
                f"embedding endpoint answered {error.status_code}"
            ) from None
        except TransportError as error:
            raise KnowledgeUnavailableError(str(error)) from None

    async def _prepare(self, texts: list[str]) -> PreparedRequest:
        body: dict[str, object] = {"model": self._model, "input": texts}
        if self._dimensions_param:
            body["dimensions"] = self._dim
        return PreparedRequest(
            url=self._endpoint,
            headers={
                "Authorization": await self._authorization(),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            body=body,
        )

def _json(response: httpx.Response) -> object:
    try:
        return response.json()
    except ValueError:
        raise KnowledgeUnavailableError("embedding response is not JSON") from None


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


def build_embedder(
    settings: Settings, client: httpx.AsyncClient, *, clock: Clock
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
            clock=clock,
            breaker=model_breaker(settings),
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
        clock=clock,
        breaker=model_breaker(settings),
    )


def _bearer(key: SecretStr) -> Callable[[], Awaitable[str]]:
    async def authorization() -> str:
        return f"Bearer {key.get_secret_value()}"

    return authorization
