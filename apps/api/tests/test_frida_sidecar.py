"""The sidecar answers in the shape the adapter validates, and refuses the rest loudly.

The process itself is not imported by the product: the module is loaded from ``scripts/`` because it
is a tool, not a package. What is tested here is the contract the adapter depends on — a bad request
is a 4xx with a reason, a dead judge is a 503, and a healthy answer is a JSON body.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]


def sidecar() -> Any:
    spec = importlib.util.spec_from_file_location(
        "frida_serve", ROOT / "scripts" / "frida_serve.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AdultJudge:
    async def judge(self, request: dict[str, Any]) -> dict[str, Any]:
        if "questions" not in request:
            raise ValueError("questions must be a non-empty object")
        return {"model": "FRIDA-Decisions", "answers": {"sentiment": {"type": "choice"}}}

    async def close(self) -> None:
        return None


def client(judge: Any = None, backend: str = "mlx") -> TestClient:
    module = sidecar()
    model = module._Model()
    model.judge = judge
    model.backend = backend
    return TestClient(module.build_app(model))


def test_a_loaded_model_answers_with_the_judge_payload() -> None:
    response = client(AdultJudge()).post("/v1/decisions", json={"state": "x", "questions": {}})

    assert response.status_code == 200
    assert response.json()["answers"]["sentiment"]["type"] == "choice"


def test_health_says_which_backend_is_serving() -> None:
    healthy = client(AdultJudge()).get("/health")
    loading = client(None).get("/health")

    assert healthy.json() == {"status": "ok", "backend": "mlx"}
    assert loading.status_code == 503


def test_a_request_the_model_refuses_is_a_422_with_the_reason() -> None:
    response = client(AdultJudge()).post("/v1/decisions", json={"state": "x"})

    assert response.status_code == 422
    assert "questions" in response.json()["error"]["message"]


def test_a_call_without_a_model_is_refused_instead_of_answered() -> None:
    response = client(None).post("/v1/decisions", json={"state": "x", "questions": {}})

    assert response.status_code == 503


def test_a_body_that_is_not_json_is_named_as_such() -> None:
    response = client(AdultJudge()).post(
        "/v1/decisions", content=b"not json", headers={"content-type": "application/json"}
    )

    assert response.status_code == 400
    assert json.loads(response.text)["error"]["type"] == "invalid_request"
