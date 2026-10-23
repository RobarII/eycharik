from __future__ import annotations

from fastapi.testclient import TestClient

from onboarding.api.app import create_app
from onboarding.app.observability import metrics
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


def test_metrics_endpoint_exposes_http_series() -> None:
    metrics.reset()
    with client() as http:
        http.get("/healthz")
        response = http.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert 'onboarding_http_requests_total{method="GET",route="/healthz",status="200"} 1' in (
        response.text
    )


def test_every_response_carries_a_request_id() -> None:
    with client() as http:
        response = http.get("/healthz", headers={"X-Request-ID": "trace-42"})

    assert response.headers["X-Request-ID"] == "trace-42"


def test_unknown_paths_do_not_become_metric_labels() -> None:
    metrics.reset()
    with client() as http:
        http.get("/there-is-no-such-route")
        http.get("/metrics")

    assert 'route="unmatched"' in http.get("/metrics").text


def expired_client() -> TestClient:
    app = create_app(
        Settings(
            _env_file=None,
            admin_tokens_raw="old:hr_admin:hr-1:2020-01-01",
            max_webhook_secret="secret",
        )
    )
    return TestClient(app)


def test_expired_admin_token_is_rejected() -> None:
    with expired_client() as http:
        response = http.get(
            "/admin/api/runs", headers={"Authorization": "Bearer old"}
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "token expired"


def test_repeated_bad_tokens_are_throttled() -> None:
    with client() as http:
        for _ in range(10):
            assert (
                http.get("/admin/api/runs", headers={"Authorization": "Bearer nope"}).status_code
                == 401
            )
        blocked = http.get(
            "/admin/api/runs", headers={"Authorization": "Bearer nope"}
        )

    assert blocked.status_code == 429


def test_metrics_can_require_a_token() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            admin_tokens_raw="token:hr_admin:hr-1",
            max_webhook_secret="secret",
            metrics_token="scrape-token",
        )
    )

    with TestClient(app) as http:
        assert http.get("/metrics").status_code == 401
        assert (
            http.get("/metrics", headers={"Authorization": "Bearer wrong"}).status_code == 401
        )
        response = http.get("/metrics", headers={"Authorization": "Bearer scrape-token"})

    assert response.status_code == 200
