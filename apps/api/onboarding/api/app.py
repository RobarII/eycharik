"""FastAPI application factory.

The app owns no global state: the container lives on ``app.state`` and is closed on shutdown, so a
test can build an app with any settings without leaking connections.
"""

from __future__ import annotations

import json
import logging
import secrets
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import PlainTextResponse

from onboarding.api import admin, errors, webhook
from onboarding.app.api_container import build_api_container
from onboarding.app.observability import metrics
from onboarding.app.settings import Settings

log = logging.getLogger(__name__)
_QUIET_PATHS = frozenset({"/healthz", "/readyz", "/metrics"})


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings()
    if not logging.getLogger().handlers:
        logging.basicConfig(level=resolved.log_level.upper(), format="%(message)s")
    docs_enabled = resolved.environment != "production"

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = build_api_container(resolved)
        try:
            yield
        finally:
            await app.state.container.aclose()

    app = FastAPI(
        title="Onboarding assistant",
        version="0.1.0",
        docs_url="/docs" if docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs_enabled else None,
        lifespan=lifespan,
    )
    errors.install(app)
    app.include_router(webhook.router)
    app.include_router(admin.router, prefix=admin.API_PREFIX)
    # Kept for a client that has not switched yet; hidden from the schema so it is not a promise.
    app.include_router(admin.router, prefix=admin.LEGACY_PREFIX, include_in_schema=False)

    @app.middleware("http")
    async def observe(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        started = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            metrics.inc(
                "onboarding_http_requests_total",
                labels={"method": request.method, "route": _route(request), "status": "500"},
            )
            raise
        elapsed = perf_counter() - started
        route = _route(request)
        labels = {"method": request.method, "route": route}
        metrics.inc(
            "onboarding_http_requests_total",
            labels={**labels, "status": str(response.status_code)},
        )
        metrics.observe("onboarding_http_request_seconds", elapsed, labels=labels)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if route.startswith("/admin/"):
            # Identity, questions and transcripts must not land in a shared cache.
            response.headers["Cache-Control"] = "no-store"
        if route not in _QUIET_PATHS:
            log.info(
                json.dumps(
                    {
                        "event": "http_request",
                        "request_id": request_id,
                        "method": request.method,
                        "route": route,
                        "status": response.status_code,
                        "latency_ms": round(elapsed * 1000, 1),
                    },
                    ensure_ascii=False,
                )
            )
        return response

    @app.get("/metrics", include_in_schema=False)
    async def prometheus(request: Request) -> Response:
        expected = resolved.metrics_token.get_secret_value()
        if expected:
            header = request.headers.get("Authorization", "")
            supplied = header.removeprefix("Bearer ")
            if not secrets.compare_digest(supplied, expected):
                return Response(status_code=status.HTTP_401_UNAUTHORIZED)
        return PlainTextResponse(metrics.render())

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    async def readyz(request: Request) -> Response:
        healthy = await request.app.state.container.health.ping()
        if not healthy:
            return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(status_code=status.HTTP_200_OK)

    return app


def _route(request: Request) -> str:
    """A route template keeps label cardinality bounded; a 404 does not leak an arbitrary path."""
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) else "unmatched"
