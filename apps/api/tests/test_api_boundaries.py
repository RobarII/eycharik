"""The API may describe HTTP; it may not touch a model, a table, or a job queue directly.

``import-linter`` catches imports. This test catches the other escape hatch: reaching through the
container into a dependency that the route was never meant to own.
"""

from __future__ import annotations

import ast
from pathlib import Path

API = Path(__file__).resolve().parents[1] / "onboarding" / "api"
ROUTES = ("admin.py", "webhook.py", "auth.py")
FORBIDDEN_ATTRS = {
    "embedder",
    "extractor",
    "knowledge",
    "llm",
    "queue",
    "service",
}
FORBIDDEN_NAMES = {
    "JobQueue",
    "PostgresKnowledgeWriter",
    "select",
    "text",
}


def _trees() -> dict[str, ast.Module]:
    return {name: ast.parse((API / name).read_text(encoding="utf-8")) for name in ROUTES}


def test_routes_do_not_reach_into_a_model_or_a_writer() -> None:
    offenders: list[str] = []
    for name, tree in _trees().items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute) or node.attr not in FORBIDDEN_ATTRS:
                continue
            receiver = node.value
            owned = (isinstance(receiver, ast.Name) and receiver.id == "container") or (
                isinstance(receiver, ast.Attribute) and receiver.attr == "container"
            )
            if owned:
                offenders.append(f"{name}:{node.lineno}: .{node.attr}")
    assert not offenders, offenders


def test_routes_do_not_import_a_repository_or_a_query_builder() -> None:
    offenders: list[str] = []
    for name, tree in _trees().items():
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
                offenders.append(f"{name}:{node.lineno}: {node.id}")
    assert not offenders, offenders


def test_the_api_container_has_no_model_or_extractor() -> None:
    source = (Path(__file__).resolve().parents[1] / "onboarding/app/api_container.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    annotations: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.AnnAssign) or not isinstance(node.target, ast.Name):
            continue
        annotations.add(ast.unparse(node.annotation))
    forbidden = {
        "LLM",
        "Embedder",
        "DocumentExtractor",
        "Answerer",
        "PostgresKnowledgeWriter",
        "httpx.AsyncClient",
    }
    assert not annotations & forbidden, sorted(annotations & forbidden)
