"""Readiness is one round trip, and it must answer instead of raise.

A load balancer cannot read a traceback: a dead database is a 503, not a 500 with a connection
string in it. The unit half proves the endpoint; the integration half proves the ping against a
real server and a real failure.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from onboarding.api.app import create_app
from onboarding.app.db.health import DatabaseHealth
from onboarding.app.db.session import Database
from onboarding.app.settings import Settings


def client() -> TestClient:
    return TestClient(
        create_app(
            Settings(
                _env_file=None,
                admin_tokens_raw="token:hr_admin:hr-1",
                max_webhook_secret="secret",
            )
        )
    )


def test_readyz_is_503_when_the_database_does_not_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def dead(self: DatabaseHealth) -> bool:
        del self
        return False

    monkeypatch.setattr(DatabaseHealth, "ping", dead)

    with client() as http:
        response = http.get("/readyz")

    assert response.status_code == 503


def test_readyz_is_200_when_the_database_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    async def alive(self: DatabaseHealth) -> bool:
        del self
        return True

    monkeypatch.setattr(DatabaseHealth, "ping", alive)

    with client() as http:
        response = http.get("/readyz")

    assert response.status_code == 200


async def test_a_ping_that_raises_is_a_false_not_a_crash() -> None:
    class Broken:
        def session(self) -> object:
            raise RuntimeError("pool is closed")

    assert await DatabaseHealth(Broken()).ping() is False  # type: ignore[arg-type]


@pytest.mark.integration
async def test_the_ping_reaches_a_real_postgres() -> None:
    url = os.environ.get("ONBOARDING_TEST_DATABASE")
    if not url:
        pytest.skip("ONBOARDING_TEST_DATABASE is not set")
    database = Database(url)
    try:
        assert await DatabaseHealth(database).ping() is True
    finally:
        await database.dispose()


@pytest.mark.integration
async def test_the_ping_answers_false_for_an_unreachable_server() -> None:
    database = Database("postgresql+asyncpg://onboarding:x@127.0.0.1:1/none")
    try:
        assert await DatabaseHealth(database).ping() is False
    finally:
        await database.dispose()
