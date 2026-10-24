"""Documentation hygiene: index, links, frontmatter, language, contracts.

A docs tree without checks rots on the first rename. This script is the gate:

- the index is generated and matches the tree (``scripts/docs_index.py``);
- every frontmatter block has the required fields;
- every relative link and every ``#anchor`` resolves;
- every ``make`` target and every repository path in backticks exists;
- every ADR has a number, a status, and symmetric ``supersedes`` links;
- every document is Russian, every measurement is short and cites its command;
- the admin contract lists exactly the routes FastAPI serves.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import docs_index
import yaml

from onboarding.api.app import create_app
from onboarding.app.settings import Settings

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MAKEFILE = ROOT / "Makefile"
GLOSSARY = DOCS / "glossary.yaml"
LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
ROUTE_ROW = re.compile(r"^\|\s*`(GET|POST|PUT|PATCH|DELETE)`\s*\|\s*(.+?)\s*\|", re.M)
BACKTICK = re.compile(r"`([^`]+)`")
ADR_TITLE = re.compile(r"^#\s+(\d{4})[\s:—–-]", re.M)
ADR_NAME = re.compile(r"^(\d{4})-")
FENCE = re.compile(r"^```")
HEADING = re.compile(r"^(#{1,6})\s+(.+)$")
H1 = re.compile(r"^#\s+", re.M)
CYRILLIC = re.compile(r"[А-Яа-яЁё]")
LATIN_WORD = re.compile(r"\b[A-Za-z][A-Za-z'’-]{2,}\b")
ANCHOR_HOST = re.compile(r"^(?:[a-z]+://|mailto:|/|#)")
PATH_LIKE = re.compile(r"^(?:apps|scripts|knowledge|infra|docs|deploy)/")
PROMPT_VERSION = re.compile(r"^v(\d+)$")
MEASURED_QUALITY = re.compile(
    r"\b(?:recall@5|recall_at_5)\s*(?:=|—|-)?\s*\d"
    r"|\bp95(?:_[a-z_]+)?\s*(?:около|≈|~|=)?\s*\d+(?:[.,]\d+)?\s*(?:мс|ms|с|сек|секунд)\b",
    re.IGNORECASE,
)

SKIP_LANGUAGE = {"docs/README.md", "docs/glossary.md"}
MEASUREMENT_MAX_LINES = 200

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
    docs = docs_index.documents()

    problems.extend(docs_index.validate(docs))
    problems.extend(_index_problems())
    problems.extend(_link_problems())
    problems.extend(_anchor_problems())
    problems.extend(_make_problems())
    problems.extend(_path_problems())
    problems.extend(_language_problems())
    problems.extend(_adr_problems(docs))
    problems.extend(_glossary_problems())
    problems.extend(_measurement_problems())
    problems.extend(_product_number_problems())
    problems.extend(_prompt_problems())
    problems.extend(_route_problems())

    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print(f"docs ok: {len(docs)} documents")
    for line in docs_index.staleness(docs):
        print(f"warning: {line}", file=sys.stderr)
    return 0


def _index_problems() -> list[str]:
    docs = docs_index.documents()
    expected = {
        docs_index.INDEX: docs_index.render_index(docs),
        docs_index.GLOSSARY_MD: docs_index.render_glossary(),
    }
    problems: list[str] = []
    for path, text in expected.items():
        actual = path.read_text(encoding="utf-8") if path.exists() else ""
        if actual != text:
            problems.append(f"{_rel(path)}: generated index is stale, run make docs-index")
    return problems


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _link_problems() -> list[str]:
    problems: list[str] = []
    for path in sorted(DOCS.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for target in LINK.findall(text):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            destination = (path.parent / target.split("#")[0]).resolve()
            if not destination.exists():
                problems.append(f"dead link in {_rel(path)}: {target}")
    return problems


def _slug(heading: str) -> str:
    text = heading.strip().lower()
    text = re.sub(r"`|\*|_", "", text)
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return re.sub(r"\s+", "-", text)


def _anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    fenced = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = HEADING.match(line)
        if match:
            anchors.add(_slug(match.group(2)))
    return anchors


def _anchor_problems() -> list[str]:
    problems: list[str] = []
    for path in sorted(DOCS.rglob("*.md")):
        for target in LINK.findall(path.read_text(encoding="utf-8")):
            if "#" not in target or target.startswith(("http://", "https://")):
                continue
            file_part, _, anchor = target.partition("#")
            if not anchor:
                continue
            destination = (path.parent / file_part).resolve() if file_part else path
            if not destination.exists() or destination.suffix != ".md":
                continue
            if anchor not in _anchors(destination):
                problems.append(f"dead anchor in {_rel(path)}: {target}")
    return problems


def _make_problems() -> list[str]:
    targets = set(re.findall(r"^([A-Za-z0-9_-]+):", MAKEFILE.read_text(encoding="utf-8"), re.M))
    problems: list[str] = []
    for path in sorted(DOCS.rglob("*.md")):
        for target in set(BACKTICK.findall(path.read_text(encoding="utf-8"))):
            match = re.match(r"^make\s+([A-Za-z0-9_-]+)", target)
            if match and match.group(1) not in targets:
                problems.append(f"{_rel(path)}: make target {match.group(1)} does not exist")
    return problems


def _path_problems() -> list[str]:
    """A path in backticks is a promise the file exists; a rename must not leave it behind."""
    problems: list[str] = []
    for path in sorted(DOCS.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for token in set(BACKTICK.findall(text)):
            candidate = token.split("#")[0].split("?")[0].strip()
            if not PATH_LIKE.match(candidate) or " " in candidate or "*" in candidate:
                continue
            if any(mark in candidate for mark in "<>{}*") or (ROOT / candidate).exists():
                continue
            problems.append(f"{_rel(path)}: path does not exist: {token}")
    return problems


def _language_problems() -> list[str]:
    """Docs are Russian. A line of English prose is a leftover translation, not a fact."""
    problems: list[str] = []
    for path in sorted(DOCS.rglob("*.md")):
        rel = _rel(path)
        if rel in SKIP_LANGUAGE:
            continue
        text = path.read_text(encoding="utf-8")
        if not CYRILLIC.search(text):
            problems.append(f"{rel}: no Russian text")
            continue
        if path.parent.name == "measurements":
            continue
        fenced = False
        for number, line in enumerate(text.splitlines(), start=1):
            if FENCE.match(line):
                fenced = not fenced
                continue
            if fenced or not line.strip() or line.lstrip().startswith(("|", "-", "#", ">", "*")):
                continue
            if CYRILLIC.search(line):
                continue
            prose = re.sub(r"\([^)]*\)|https?://\S+|`[^`]*`|\[[^\]]*\]", " ", line)
            if len(LATIN_WORD.findall(prose)) >= 8:
                problems.append(f"{rel}:{number}: English prose left in a Russian document")
    return problems


def _adr_problems(docs: list[docs_index.Doc]) -> list[str]:  # noqa: PLR0912 - one rule per ADR field
    """One number names one file; replacement links point both ways."""
    problems: list[str] = []
    seen: dict[str, Path] = {}
    numbers: dict[int, docs_index.Doc] = {}
    for doc in docs:
        if doc.kind != "решение":
            continue
        path = doc.path
        match = ADR_NAME.match(path.name)
        if match is None:
            problems.append(f"ADR without a number: {path.name}")
            continue
        number = match.group(1)
        if number in seen:
            problems.append(f"duplicate ADR {number}: {seen[number].name} and {path.name}")
        seen[number] = path
        numbers[int(number)] = doc
        title = ADR_TITLE.search(path.read_text(encoding="utf-8"))
        if title is None:
            problems.append(f"ADR without a numbered title: {path.name}")
        elif title.group(1) != number:
            problems.append(f"ADR {number} has title number {title.group(1)}: {path.name}")
        status = str(doc.meta.get("status"))
        if status == "предложено" and "Критерии выхода" not in path.read_text(encoding="utf-8"):
            problems.append(f"ADR {number}: status «предложено» without section «Критерии выхода»")
    for number, doc in numbers.items():
        for other in doc.meta.get("supersedes", []) or []:
            target = numbers.get(int(other))
            if target is None:
                problems.append(f"ADR {number}: supersedes unknown ADR {other}")
            elif number not in (target.meta.get("superseded_by") or []):
                problems.append(
                    f"ADR {number} supersedes {other}, but {other} has no superseded_by {number}"
                )
        for other in doc.meta.get("superseded_by", []) or []:
            target = numbers.get(int(other))
            if target is None:
                problems.append(f"ADR {number}: superseded_by unknown ADR {other}")
            elif number not in (target.meta.get("supersedes") or []):
                problems.append(
                    f"ADR {number} superseded_by {other}, but {other} has no supersedes {number}"
                )
    return problems


def _glossary_problems() -> list[str]:
    entries = yaml.safe_load(GLOSSARY.read_text(encoding="utf-8"))
    terms = [str(entry["term"]) for entry in entries]
    duplicates = {term for term in terms if terms.count(term) > 1}
    problems = [f"glossary: duplicate term {term}" for term in sorted(duplicates)]
    body = "\n".join(
        path.read_text(encoding="utf-8")
        for path in DOCS.rglob("*.md")
        if path.name not in {"glossary.md"}
    )
    for entry in entries:
        names = [str(entry["term"]), *(str(alias) for alias in entry.get("aliases", []))]
        if not any(_used(name, body) for name in names):
            problems.append(f"glossary: term {entry['term']} is not used anywhere")
    for entry in entries:
        if not entry.get("aliases"):
            problems.append(
                f"glossary: term {entry['term']} has no alias, the code uses English names"
            )
    return problems


def _used(term: str, body: str) -> bool:
    """Термин считается использованным, если в тексте есть основа каждого его слова."""
    lowered = body.lower()
    stems = [word[:5] for word in re.findall(r"[\w-]{4,}", term.lower())]
    return bool(stems) and all(stem in lowered for stem in stems)


def _measurement_problems() -> list[str]:
    problems: list[str] = []
    for path in sorted((DOCS / "measurements").glob("*.md")):
        if path.name == "TEMPLATE.md":
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) > MEASUREMENT_MAX_LINES:
            problems.append(
                f"{_rel(path)}: {len(lines)} lines, the summary must fit {MEASUREMENT_MAX_LINES}"
            )
        for required in ("- команда:", "- коммит:", "- окружение:"):
            if not any(line.startswith(required) for line in lines):
                problems.append(f"{_rel(path)}: missing line {required!r}")
        if any(line.startswith("## Cases") or line.startswith("### `") for line in lines):
            problems.append(f"{_rel(path)}: per-case dump belongs to the jsonl artifact")
    return problems


def _product_number_problems() -> list[str]:
    """Product prose points at the numbers; it does not carry its own copy.

    Latency and retrieval quality move with every full run. A product page that quotes them rots
    silently, which is exactly what happened to the defence script: 16 cases and 2.2 s while the
    current set had 137 cases and 29 s. Prices and derived arithmetic stay allowed.
    """
    problems: list[str] = []
    for path in sorted((DOCS / "product").glob("*.md")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "measurements/" in line:
                continue
            if MEASURED_QUALITY.search(line):
                problems.append(
                    f"{_rel(path)}:{number}: measured quality number outside docs/measurements/ "
                    "— link to measurements/current.md instead"
                )
    return problems


def _prompt_problems() -> list[str]:
    problems: list[str] = []
    for directory in sorted((DOCS / "prompts").iterdir()):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            if not PROMPT_VERSION.match(path.stem):
                problems.append(f"{_rel(path)}: prompt version must be vN")
                continue
            meta_path = path.with_suffix(".meta.yaml")
            if not meta_path.exists():
                problems.append(f"{_rel(path)}: no {meta_path.name} next to the prompt")
                continue
            meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
            if int(meta.get("version", 0)) != int(path.stem[1:]):
                problems.append(f"{meta_path.name}: version does not match {path.name}")
            if meta.get("eval") and not (ROOT / str(meta["eval"])).exists():
                problems.append(f"{meta_path.name}: eval file {meta['eval']} does not exist")
            if not str(meta.get("notes", "")).strip():
                problems.append(
                    f"{meta_path.name}: notes are empty, a prompt version must say what changed"
                )
            elif not CYRILLIC.search(str(meta.get("notes", ""))):
                problems.append(f"{meta_path.name}: notes must be Russian")
    return problems


def _documented_routes() -> set[tuple[str, str]]:
    contract = (DOCS / "contracts" / "admin-api.md").read_text(encoding="utf-8")
    routes: set[tuple[str, str]] = set()
    for method, cell in ROUTE_ROW.findall(contract):
        for target in BACKTICK.findall(cell):
            routes.add((method, _canonical(target.split("?")[0])))
    return routes


def _canonical(path: str) -> str:
    """Drop the cabinet's version prefix so the alias and the contract compare as one surface."""
    for prefix in ("/admin/api/v1", "/admin/api"):
        if path == prefix:
            return "/"
        if path.startswith(prefix + "/"):
            return path[len(prefix) :]
    return path


def _app_routes() -> set[tuple[str, str]]:
    app = create_app(Settings(_env_file=None))
    return {(method, _canonical(path)) for method, path in _walk(app.routes)}


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
