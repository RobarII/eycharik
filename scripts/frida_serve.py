#!/usr/bin/env python3
"""Serve FRIDA-Decisions over HTTP so the classifier adapter can reach it (ADR 0037).

The model ships four runtimes and none of them is an HTTP server on Apple Silicon: vLLM lives on
Linux, and the MLX, ONNX and PyTorch judges are libraries. This script is the missing process — it
loads one judge, batches concurrent requests through `AsyncJudge`, and exposes the request format
from `frida_decisions.protocol` on `POST <prefix>/decisions`, which is exactly what the adapter in
``apps/api/onboarding/app/llm/decisions.py`` posts.

Run it with the package installed next to this repository, not inside the product venv:

    uv run --with 'frida-decisions[mlx] @ git+https://github.com/ai-forever/FRIDA-Decisions@v0.4.0' \
        python scripts/frida_serve.py --backend mlx --port 8090

    CLASSIFY_PROFILE=local-frida-decisions \\
    CLASSIFY_BASE_URL=http://127.0.0.1:8090/v1 \\
    SENTIMENT_PROVIDER=decisions \\
    make eval-sentiment PROVIDER=decisions

`--model` takes a directory (`hf download ai-forever/FRIDA-Decisions --local-dir ~/models/frida-decisions`)
or a Hub repo id, which the package downloads itself.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, Protocol

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

PREFIX_DEFAULT = "/v1"
PATH = "/decisions"


class _Judge(Protocol):
    async def judge(self, request: dict[str, Any]) -> dict[str, Any]: ...

    async def close(self) -> None: ...


class _Model:
    """The loaded judge, or the reason it is not loaded. One process, one model."""

    judge: _Judge | None = None
    backend: str = ""


def build_app(model: _Model, prefix: str = PREFIX_DEFAULT) -> FastAPI:
    app = FastAPI(title="frida-decisions sidecar", version="0.4.0")

    @app.get("/health")
    async def health() -> JSONResponse:
        if model.judge is None:
            return JSONResponse({"status": "loading"}, status_code=503)
        return JSONResponse({"status": "ok", "backend": model.backend})

    @app.post(f"{prefix}{PATH}")
    async def decisions(request: Request) -> JSONResponse:
        if model.judge is None:
            return JSONResponse({"error": {"message": "model is not loaded"}}, status_code=503)
        try:
            body = await request.json()
        except ValueError:
            return JSONResponse(
                {"error": {"type": "invalid_request", "message": "body is not JSON"}},
                status_code=400,
            )
        try:
            # `parse_request` validates before the model runs, so a bad rubric costs no forward.
            answer = await model.judge.judge(body)
        except ValueError as error:
            # `RequestError` carries a field and an HTTP status; anything else is a plain 422.
            payload = getattr(error, "payload", None)
            body_out: dict[str, Any] = (
                payload() if callable(payload) else {"error": {"message": str(error)[:500]}}
            )
            field = getattr(error, "field", None)
            if field and "field" not in body_out.get("error", {}):
                body_out["error"]["field"] = field
            return JSONResponse(body_out, status_code=getattr(error, "status", 422))
        except Exception as error:  # noqa: BLE001 - a serving process reports, it does not crash
            detail = f"{type(error).__name__}: {error}"[:500]
            return JSONResponse({"error": {"type": "internal", "message": detail}}, status_code=500)
        return JSONResponse(answer)

    return app


def load(
    backend: str,
    model_path: str,
    *,
    state_max: int,
    max_batch: int,
    wait_ms: float,
    dtype: str,
) -> _Judge:
    """One judge, wrapped so that requests arriving together share encoder forwards."""
    from frida_decisions import AsyncJudge

    kwargs: dict[str, Any] = {"state_max": state_max}
    if backend == "mlx":
        import mlx.core as mx

        kwargs["dtype"] = getattr(mx, dtype)
    elif backend == "torch":
        import torch

        kwargs["dtype"] = getattr(torch, dtype)
    judge: _Judge = AsyncJudge.from_pretrained(model_path, backend=backend, **kwargs)
    judge.max_batch = max_batch  # type: ignore[attr-defined]
    judge.max_wait = wait_ms / 1000.0  # type: ignore[attr-defined]
    return judge


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HTTP sidecar for ai-forever/FRIDA-Decisions")
    parser.add_argument("--model", default="ai-forever/FRIDA-Decisions")
    parser.add_argument("--backend", choices=["mlx", "onnx", "torch"], default="mlx")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--prefix", default=PREFIX_DEFAULT)
    parser.add_argument(
        "--state-max",
        type=int,
        default=512,
        help="state tokens; the released config says 512 and the adapter truncates to it",
    )
    parser.add_argument(
        "--dtype",
        choices=["float32", "bfloat16"],
        default="bfloat16",
        help="encoder precision; bfloat16 is the released weight type, float32 is the reference",
    )
    parser.add_argument("--max-batch", type=int, default=8)
    parser.add_argument("--wait-ms", type=float, default=5.0)
    args = parser.parse_args(argv)

    import uvicorn

    model = _Model()
    app = build_app(model, args.prefix)

    @app.on_event("startup")
    async def _load() -> None:  # pragma: no cover - exercised by the serving process only
        model.judge = load(
            args.backend,
            args.model,
            state_max=args.state_max,
            max_batch=args.max_batch,
            wait_ms=args.wait_ms,
            dtype=args.dtype,
        )
        model.backend = args.backend

    print(
        f"frida-decisions sidecar: backend {args.backend} {args.dtype}, model {args.model}, "
        f"POST http://{args.host}:{args.port}{args.prefix}{PATH}",
        file=sys.stderr,
    )
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
