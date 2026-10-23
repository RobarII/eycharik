"""The embedding adapter: strict dimensions and a retry for cheap gateways."""

from __future__ import annotations

import httpx
import pytest

from onboarding.app.llm.embeddings import RemoteEmbedder
from onboarding.ports import KnowledgeUnavailableError


def embedder(client: httpx.AsyncClient, dim: int = 3) -> RemoteEmbedder:
    async def authorization() -> str:
        return "Bearer secret"

    return RemoteEmbedder(
        client=client,
        endpoint="https://example.test/embeddings",
        authorization=authorization,
        model="model",
        dim=dim,
        timeout_s=1.0,
    )


def vector_payload(count: int, dim: int = 3) -> dict[str, object]:
    return {
        "data": [
            {"index": index, "embedding": [float(index)] * dim} for index in range(count)
        ]
    }


async def test_retries_a_transient_failure() -> None:
    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) < 3:
            return httpx.Response(503)
        return httpx.Response(200, json=vector_payload(2))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        vectors = await embedder(client).embed(("а", "б"))

    assert len(attempts) == 3
    assert vectors == ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))


async def test_a_wrong_dimension_is_a_hard_error() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=vector_payload(1, dim=2))
    )
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(KnowledgeUnavailableError, match="3-dimensional"):
            await embedder(client).embed(("а",))


async def test_a_client_error_is_not_retried() -> None:
    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        return httpx.Response(401)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(KnowledgeUnavailableError, match="401"):
            await embedder(client).embed(("а",))

    assert len(attempts) == 1
