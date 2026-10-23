from __future__ import annotations

from collections.abc import Iterator

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


def test_webhook_rejects_invalid_json() -> None:
    with client() as http:
        response = http.post(
            "/webhook",
            content=b"not json",
            headers={"X-Max-Bot-Api-Secret": "secret"},
        )

    assert response.status_code == 400


def test_webhook_limits_a_streamed_body() -> None:
    def chunks() -> Iterator[bytes]:
        yield b"{"
        yield b" " * 1_000_001

    with client() as http:
        response = http.post(
            "/webhook",
            content=chunks(),
            headers={"X-Max-Bot-Api-Secret": "secret"},
        )

    assert response.status_code == 413


def test_me_describes_the_recruiter_scope_and_capabilities() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            admin_tokens_raw="rec:recruiter:rec-1",
            max_webhook_secret="secret",
        )
    )
    with TestClient(app) as http:
        response = http.get("/admin/api/me", headers={"Authorization": "Bearer rec"})

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "recruiter"
    assert body["scope"] == {"recruiter_id": "rec-1", "department": None}
    assert body["expires_at"] is None
    assert "questions.resolve" in body["capabilities"]
    assert "knowledge.write" not in body["capabilities"]
    assert "employees.offboard" not in body["capabilities"]


def test_me_scopes_a_manager_by_department_and_grants_no_writes() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            admin_tokens_raw="mgr:manager:ИТ",
            max_webhook_secret="secret",
        )
    )
    with TestClient(app) as http:
        body = http.get("/admin/api/me", headers={"Authorization": "Bearer mgr"}).json()

    assert body["scope"] == {"recruiter_id": None, "department": "ИТ"}
    assert "knowledge.write" not in body["capabilities"]


def test_me_reports_the_full_hr_capability_set_and_expiry() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            admin_tokens_raw="hr:hr_admin:hr-1:2030-12-31",
            max_webhook_secret="secret",
        )
    )
    with TestClient(app) as http:
        response = http.get("/admin/api/me", headers={"Authorization": "Bearer hr"})

    body = response.json()
    assert body["role"] == "hr_admin"
    assert body["scope"] == {"recruiter_id": None, "department": None}
    assert set(body["capabilities"]) >= {"knowledge.write", "employees.offboard"}
    assert body["expires_at"].startswith("2031-01-01T00:00:00")


def test_me_requires_a_token() -> None:
    with client() as http:
        assert http.get("/admin/api/me").status_code == 401


def session_client(raw: str = "rec:recruiter:rec-1") -> TestClient:
    app = create_app(
        Settings(_env_file=None, admin_tokens_raw=raw, max_webhook_secret="secret")
    )
    return TestClient(app)


def test_session_trades_a_token_for_an_httponly_cookie() -> None:
    with session_client() as http:
        response = http.post("/admin/api/session", json={"token": "rec"})

    assert response.status_code == 204
    cookie = response.headers["set-cookie"]
    assert cookie.startswith("onboarding_session=rec;")
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie.replace("samesite", "SameSite")
    assert "Path=/admin/api" in cookie
    # A local stack is served over plain http, so the cookie must not demand TLS there.
    assert "Secure" not in cookie


def test_the_cookie_alone_authenticates() -> None:
    with session_client() as http:
        http.post("/admin/api/session", json={"token": "rec"})
        http.headers.pop("Authorization", None)
        response = http.get("/admin/api/me")

    assert response.status_code == 200
    assert response.json()["subject"] == "rec-1"


def test_a_bad_token_opens_no_session() -> None:
    with session_client() as http:
        response = http.post("/admin/api/session", json={"token": "nope"})

    assert response.status_code == 401
    assert "set-cookie" not in response.headers


def test_expired_token_opens_no_session() -> None:
    with session_client("old:hr_admin:hr-1:2020-01-01") as http:
        response = http.post("/admin/api/session", json={"token": "old"})

    assert response.status_code == 401
    assert response.json()["detail"] == "token expired"


def test_signing_out_clears_the_cookie_without_a_valid_token() -> None:
    with session_client() as http:
        response = http.delete("/admin/api/session")

    assert response.status_code == 204
    assert 'onboarding_session=""' in response.headers["set-cookie"]
    assert "Max-Age=0" in response.headers["set-cookie"]


def test_api_responses_forbid_sniffing_and_caching_of_identity() -> None:
    with session_client() as http:
        response = http.get("/admin/api/me", headers={"Authorization": "Bearer rec"})

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"


def test_a_malformed_cursor_is_a_bad_request_not_a_partial_page() -> None:
    app = create_app(
        Settings(_env_file=None, admin_tokens_raw="rec:recruiter:rec-1", max_webhook_secret="secret")
    )
    with TestClient(app) as http:
        runs = http.get(
            "/admin/api/runs?cursor=not-a-cursor", headers={"Authorization": "Bearer rec"}
        )
        questions = http.get(
            "/admin/api/questions?cursor=not-a-cursor", headers={"Authorization": "Bearer rec"}
        )

    assert runs.status_code == 400
    assert runs.json()["detail"] == "cursor is not valid"
    assert questions.status_code == 400
