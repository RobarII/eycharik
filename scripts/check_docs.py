"""Documentation hygiene: the index is complete and every link resolves.

A docs tree without an index is a pile of files. This check keeps `docs/README.md` honest and
catches a rename that left a dead link behind.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from onboarding.api.app import create_app
from onboarding.app.settings import Settings

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
INDEX = DOCS / "README.md"
LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
ROUTE_ROW = re.compile(r"^\|\s*`(GET|POST|PUT|PATCH|DELETE)`\s*\|\s*(.+?)\s*\|", re.M)
BACKTICK = re.compile(r"`([^`]+)`")
ADR_TITLE = re.compile(r"^#\s+(\d{4})[\s:—-]", re.M)
ADR_NAME = re.compile(r"^(\d{4})-")

SKIP = {"README.md"}
# Internal surfaces: the MAX webhook, the scrape endpoint, and FastAPI's own pages.
UNDOCUMENTED = {
    "/webhook/{channel}",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/docs/oauth2-redirect",
}


def main() -> int:
    problems: list[str] = []
    index_text = INDEX.read_text(encoding="utf-8")
    linked = {
        (INDEX.parent / target).resolve()
        for target in LINK.findall(index_text)
        if not target.startswith(("http://", "https://", "#"))
    }

    for path in sorted(DOCS.rglob("*.md")):
        if path.name in SKIP or path.parent.name in {"measurements", "incidents"}:
            continue
        if path.resolve() not in linked:
            problems.append(f"not in docs/README.md: {path.relative_to(DOCS.parent)}")

    for path in sorted(DOCS.rglob("*.md")):
        for target in LINK.findall(path.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            destination = (path.parent / target.split("#")[0]).resolve()
            if not destination.exists():
                problems.append(
                    f"dead link in {path.relative_to(DOCS.parent)}: {target}"
                )

    problems.extend(_route_problems())
    problems.extend(_adr_problems())

    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print(f"docs ok: {len(list(DOCS.rglob('*.md')))} files")
    return 0


def _documented_routes() -> set[tuple[str, str]]:
    contract = (DOCS / "contracts" / "admin-api.md").read_text(encoding="utf-8")
    routes: set[tuple[str, str]] = set()
    for method, cell in ROUTE_ROW.findall(contract):
        for target in BACKTICK.findall(cell):
            routes.add((method, target.split("?")[0]))
    return routes


def _app_routes() -> set[tuple[str, str]]:
    app = create_app(Settings(_env_file=None))
    return set(_walk(app.routes))


def _walk(routes: Iterable[Any]) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for route in routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if isinstance(path, str) and isinstance(methods, set):
            for method in methods:
                if method not in {"HEAD", "OPTIONS"}:
                    found.append((method, path))
        inner = getattr(route, "original_router", None)
        if inner is not None:
            found.extend(_walk(inner.routes))
    return found


def _adr_problems() -> list[str]:
    """Each ADR number names one file and one title; a duplicate makes a reference ambiguous."""
    seen: dict[str, Path] = {}
    problems: list[str] = []
    for path in sorted((DOCS / "decisions").glob("*.md")):
        if path.name == "README.md":
            continue
        match = ADR_NAME.match(path.name)
        if match is None:
            problems.append(f"ADR without a number: {path.name}")
            continue
        number = match.group(1)
        if number in seen:
            problems.append(f"duplicate ADR {number}: {seen[number].name} and {path.name}")
        seen[number] = path
        title = ADR_TITLE.search(path.read_text(encoding="utf-8"))
        if title is None:
            problems.append(f"ADR without a numbered title: {path.name}")
        elif title.group(1) != number:
            problems.append(f"ADR {number} has title number {title.group(1)}: {path.name}")
        if not re.search(r"^-?\s*Status:", path.read_text(encoding="utf-8"), re.M):
            problems.append(f"ADR without a Status line: {path.name}")
    return problems


def _route_problems() -> list[str]:
    """The admin contract and the FastAPI routes must describe the same surface.

    A contract that lists a route nobody serves misleads the cabinet; a route nobody documented is
    a mutation the reviewer never saw. The check runs in CI on every pull request.
    """
    documented = _documented_routes()
    served = _app_routes()
    problems: list[str] = []
    for method, path in sorted(documented - served):
        problems.append(f"contract documents {method} {path}, no such route")
    for method, path in sorted(served - documented):
        if path in UNDOCUMENTED:
            continue
        problems.append(f"route {method} {path} is missing from docs/contracts/admin-api.md")
    return problems


if __name__ == "__main__":
    sys.exit(main())
