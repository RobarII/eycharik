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


async def test_vectors_come_back_in_request_order() -> None:
    payload = {
        "data": [
            {"index": 1, "embedding": [1.0, 1.0, 1.0]},
            {"index": 0, "embedding": [0.0, 0.0, 0.0]},
        ]
    }
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    async with httpx.AsyncClient(transport=transport) as client:
        vectors = await embedder(client).embed(("а", "б"))

    assert vectors == ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({}, "wrong number of vectors"),
        ({"data": [{"embedding": [0.0, 0.0, 0.0]}]}, "no integer index"),
        ({"data": [{"index": "0", "embedding": [0.0, 0.0, 0.0]}]}, "no integer index"),
        ({"data": [{"index": 3, "embedding": [0.0, 0.0, 0.0]}]}, "out of range"),
        (
            {
                "data": [
                    {"index": 0, "embedding": [0.0, 0.0, 0.0]},
                    {"index": 0, "embedding": [1.0, 1.0, 1.0]},
                ]
            },
            "repeated",
        ),
        ({"data": [{"index": 0, "embedding": ["x", 0.0, 0.0]}]}, "non-numeric"),
        ({"data": [{"index": 0, "embedding": None}]}, "3-dimensional"),
        ({"data": ["nope"]}, "not an object"),
    ],
)
async def test_a_malformed_envelope_is_a_typed_outage(
    payload: dict[str, object], message: str
) -> None:
    """A provider bug reaches the retry policy as ``KnowledgeUnavailableError``.

    A ``KeyError`` three frames inside the worker is not something the retry policy can recognise,
    so the turn fails instead of degrading to an outage the pipeline already handles.
    """
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    count = len(payload.get("data", ()))  # type: ignore[arg-type]
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(KnowledgeUnavailableError, match=message):
            await embedder(client).embed(tuple("аб"[: max(1, count)]))
