"""FastAPI application factory.

The app owns no global state: the container lives on ``app.state`` and is closed on shutdown, so a
test can build an app with any settings without leaking connections.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from sqlalchemy import text

from onboarding.api import admin, webhook
from onboarding.app.container import build_container
from onboarding.app.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings()
    docs_enabled = resolved.environment != "production"

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = build_container(resolved)
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
    app.include_router(webhook.router)
    app.include_router(admin.router)

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    async def readyz(request: Request) -> Response:
        try:
            async with request.app.state.container.database.session() as session:
                await session.execute(text("select 1"))
        except Exception:  # noqa: BLE001 - readiness must answer, not raise
            return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(status_code=status.HTTP_200_OK)

    return app
