"""Two tiers of tests, and the machinery that keeps the cheap tier cheap.

The default run is offline: no provider key is used, no request leaves the process, and a test that
tries anyway fails with a message naming the marker it forgot. Live suites — a real Postgres
(``integration``) and a real model provider (``eval``) — run only when asked for:

    make test        # offline: ruff, mypy, unit tests
    make test-live   # integration + eval markers, spends tokens

The isolation is deliberate, not incidental. ``.env.local`` points at paid endpoints, and a suite
that quietly reads it turns `make check` into an invoice. Config is not pinned — provider-profile
tests need to rewrite it — so the boundary is the transport: an offline test cannot open a socket.
"""

from __future__ import annotations

import socket
from collections.abc import Iterator
from datetime import UTC, datetime

import httpx
import pytest

from onboarding.api.ratelimit import auth_failures
from onboarding.core.models import (
    ChunkId,
    EmployeeId,
    Event,
    EventKind,
    RunId,
    Scenario,
    StepState,
)
from onboarding.core.scenario import parse_scenario

NOW = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)

_LOOPBACK = {"127.0.0.1", "::1", "localhost", "testserver"}


def _allows_network(request: pytest.FixtureRequest) -> bool:
    return any(marker in request.node.keywords for marker in ("integration", "eval"))


@pytest.fixture(autouse=True)
def _no_outbound_network(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail loudly on a real request from the offline tier.

    ``httpx.MockTransport`` replaces the transport itself, so mocked clients keep working; only a
    client that would open a socket is stopped.
    """
    if _allows_network(request):
        return

    async def blocked_async(
        self: httpx.AsyncHTTPTransport, request: httpx.Request
    ) -> httpx.Response:
        raise AssertionError(
            f"offline test tried to reach {request.url.host}; mark it `eval` or `integration`"
        )

    def blocked_sync(self: httpx.HTTPTransport, request: httpx.Request) -> httpx.Response:
        raise AssertionError(
            f"offline test tried to reach {request.url.host}; mark it `eval` or `integration`"
        )

    def blocked_connect(self: socket.socket, address: object) -> None:
        host = address[0] if isinstance(address, tuple) else address
        if isinstance(host, str) and host in _LOOPBACK:
            raise AssertionError(
                "offline test opened a socket; use httpx.MockTransport or the ASGI client"
            )
        raise AssertionError(f"offline test opened a socket to {host}")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", blocked_async)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked_sync)
    monkeypatch.setattr(socket.socket, "connect", blocked_connect)


def scenario_document() -> dict[str, object]:
    return {
        "id": "onboarding_default",
        "version": 1,
        "title": "Онбординг по умолчанию",
        "start": "welcome",
        "steps": [
            {
                "id": "welcome",
                "kind": "send",
                "message": "Добро пожаловать в компанию.",
                "next": "checklist",
            },
            {
                "id": "checklist",
                "kind": "wait",
                "message": "Отметьте первый день.",
                "expects": "button",
                "keyboard": [[{"id": "done", "text": "Готово"}]],
                "routes": {"done": "documents"},
                "timeout": {"after_hours": 48, "action": "remind"},
            },
            {
                "id": "documents",
                "kind": "wait",
                "message": "Пришлите документы.",
                "expects": "message",
                "routes": {"default": "done"},
                "timeout": {"after_hours": 72, "action": "escalate"},
            },
            {"id": "done", "kind": "terminal", "outcome": "completed"},
        ],
    }


@pytest.fixture
def scenario() -> Scenario:
    return parse_scenario(scenario_document())


@pytest.fixture
def state(scenario: Scenario) -> StepState:
    return StepState(
        run_id=RunId("run-1"),
        employee_id=EmployeeId("employee-1"),
        scenario_id=scenario.id,
        scenario_version=scenario.version,
        step_id="checklist",
        entered_at=NOW,
    )


@pytest.fixture
def message_event() -> Event:
    return Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="Когда отпуск?")


@pytest.fixture
def chunk_id() -> ChunkId:
    return ChunkId("hr/leave-policy#0")


@pytest.fixture(autouse=True)
def _reset_auth_failures() -> Iterator[None]:
    auth_failures.reset()
    yield
    auth_failures.reset()
