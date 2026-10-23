from __future__ import annotations

from fastapi.testclient import TestClient

from onboarding.api.app import create_app
from onboarding.app.settings import Settings


def client() -> TestClient:
    app = create_app(
        Settings(
            _env_file=None,
            admin_tokens_raw="token:hr_admin:hr-1",
            max_webhook_secret="secret",
        )
    )
    return TestClient(app)


def test_healthz_is_open() -> None:
    with client() as http:
        response = http.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_rejects_a_wrong_secret() -> None:
    with client() as http:
        response = http.post(
            "/webhook",
            json={"update_type": "message_created"},
            headers={"X-Max-Bot-Api-Secret": "wrong"},
        )

    assert response.status_code == 401


def test_admin_requires_a_token() -> None:
    with client() as http:
        response = http.get("/admin/api/runs")

    assert response.status_code == 401


def test_admin_rejects_an_unknown_token() -> None:
    with client() as http:
        response = http.get(
            "/admin/api/runs", headers={"Authorization": "Bearer nope"}
        )

    assert response.status_code == 401
