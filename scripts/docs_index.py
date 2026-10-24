#!/usr/bin/env python3
"""Сборка индекса документации и глоссария из frontmatter.

Индекс, написанный руками, отстаёт от дерева на первой же правке. Здесь он собирается
из frontmatter каждого файла: `make docs-index` пишет, `make docs` проверяет расхождение.

    python3 scripts/docs_index.py --write
    python3 scripts/docs_index.py --check
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
INDEX = DOCS / "README.md"
GLOSSARY_MD = DOCS / "glossary.md"
GLOSSARY = DOCS / "glossary.yaml"
SCHEMA = DOCS / "_meta" / "frontmatter.schema.json"

GENERATED = {INDEX.name, GLOSSARY_MD.name}
# Промпт — файл данных: его тело читает PromptLibrary, frontmatter сломал бы шаблон.
DATA = DOCS / "prompts"
KINDS: dict[str, str] = {
    "правило": "Правила системы",
    "контракт": "Контракты",
    "решение": "Решения (ADR)",
    "прогон": "Прогоны и восстановление",
    "продукт": "Продукт",
    "оценка": "Оценки качества",
    "измерение": "Измерения",
    "инцидент": "Инциденты",
    "кейс": "Кейс клиента",
    "промпт": "Промпты",
}
KIND_ORDER = list(KINDS)
STATUSES = {"черновик", "предложено", "принято", "заменено"}
STALE_DAYS = 90

START_HERE: tuple[tuple[str, str], ...] = (
    ("Что за система и как идёт сообщение", "architecture.md"),
    ("Как писать код, тесты и коммиты", "conventions.md"),
    ("Что значит слово", "glossary.md"),
    ("Что можно ответить сотруднику", "product/answer-policy.md"),
    ("Что вызывает кабинет", "contracts/admin-api.md"),
    ("Как выкатить и откатить", "runbooks/deploy.md"),
    ("Как измеряется качество", "evals/README.md"),
    ("Где лежат числа", "measurements/current.md"),
)

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
H1 = re.compile(r"^#\s+(.+)$", re.M)
ADR_NUMBER = re.compile(r"^(\d{4})-")


class Doc:
    def __init__(self, path: Path, meta: dict[str, Any]) -> None:
        self.path = path
        self.meta = meta

    @property
    def rel(self) -> str:
        return self.path.relative_to(DOCS).as_posix()

    @property
    def link(self) -> str:
        return f"[{self.meta['title']}]({self.rel})"

    @property
    def kind(self) -> str:
        return str(self.meta["kind"])

    @property
    def order(self) -> tuple[int, int, str]:
        match = ADR_NUMBER.match(self.path.name)
        number = int(match.group(1)) if match else 0
        return (KIND_ORDER.index(self.kind), number, self.rel)


def read_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER.match(text)
    if match is None:
        raise ValueError(f"{path.relative_to(ROOT)}: нет frontmatter")
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as error:
        raise ValueError(f"{path.relative_to(ROOT)}: frontmatter не разобран: {error}") from error
    if not isinstance(meta, dict):
        raise ValueError(f"{path.relative_to(ROOT)}: frontmatter не словарь")
    return meta, text[match.end() :]


def documents() -> list[Doc]:
    docs: list[Doc] = []
    for path in sorted(DOCS.rglob("*.md")):
        if path.name in GENERATED or DATA in path.parents:
            continue
        meta, _ = read_frontmatter(path)
        docs.append(Doc(path, meta))
    return sorted(docs, key=lambda doc: doc.order)


def _cell(value: str) -> str:
    return value.replace("|", "\\|").strip()


def render_index(docs: list[Doc]) -> str:
    lines = [
        "# Документация",
        "",
        "Индекс собран из frontmatter скриптом `scripts/docs_index.py`. Руками не править:",
        "`make docs-index` перезапишет, `make docs` упадёт при расхождении.",
        "",
        "Правила ведения — [conventions.md](conventions.md). Термины — [glossary.md](glossary.md).",
        "",
        "## С чего начать",
        "",
        "| Вопрос | Документ |",
        "|---|---|",
    ]
    for question, rel in START_HERE:
        lines.append(f"| {question} | [{rel}]({rel}) |")
    lines.append("")

    for kind in KIND_ORDER:
        group = [doc for doc in docs if doc.kind == kind]
        if not group:
            continue
        lines += [f"## {KINDS[kind]}", ""]
        if kind in {"измерение", "инцидент"}:
            for doc in group:
                lines.append(f"- {doc.link} — проверен {doc.meta['last_verified']}")
        else:
            lines += ["| Документ | О чём | Владелец | Проверен |", "|---|---|---|---|"]
            for doc in group:
                lines.append(
                    f"| {doc.link} | {_cell(str(doc.meta['summary']))} | "
                    f"`{doc.meta['owner']}` | {doc.meta['last_verified']} |"
                )
        lines.append("")

    lines += _prompt_lines()
    lines += [
        "## Файлы-данные",
        "",
        "Схемы, профили и рубрики не несут frontmatter: их читает код, а описывает документ рядом.",
        "",
        "- `docs/contracts/*.schema.json` — схемы контрактов, их описывает [contracts/](contracts/)",  # noqa: E501
        "- `docs/prompts/<роль>/<версия>.yaml` — рубрики и промпты с метаданными",
        "- `docs/evals/*.yaml` — золотые наборы и фикстуры оценок",
        "- `docs/assets/` — картинки для `product/`",
        "",
    ]
    return "\n".join(lines)


def _prompt_lines() -> list[str]:
    lines = [
        "## Промпты",
        "",
        "Тело промпта — файл, который читает код. Версии не правятся: правка — новая версия.",
        "",
    ]
    for directory in sorted(path for path in DATA.iterdir() if path.is_dir()):
        versions = sorted(
            (path for path in directory.glob("v*.md") if path.stem[1:].isdigit()),
            key=lambda path: int(path.stem[1:]),
        )
        if not versions:
            continue
        current = versions[-1]
        links = []
        for path in versions:
            rel = path.relative_to(DOCS).as_posix()
            mark = " (текущая)" if path == current else ""
            links.append(f"[v{path.stem[1:]}]({rel}){mark}")
        lines.append(f"- **{directory.name}**: " + ", ".join(links))
    lines.append("")
    return lines


def render_glossary() -> str:
    entries = yaml.safe_load(GLOSSARY.read_text(encoding="utf-8"))
    lines = [
        "# Глоссарий",
        "",
        "Собран из [glossary.yaml](glossary.yaml) скриптом `make docs-index`. Новый термин",
        "добавляется в YAML, не сюда.",
        "",
        "Одно значение на термин. Код, доки и промпты используют эти слова без синонимов.",
        "",
        "| Термин | Значение | В коде | См. также |",
        "|---|---|---|---|",
    ]
    for entry in entries:
        aliases = ", ".join(f"`{alias}`" for alias in entry.get("aliases", []))
        see = ", ".join(entry.get("see", []))
        lines.append(
            f"| **{_cell(entry['term'])}** | {_cell(entry['definition'])} | "
            f"{aliases or '—'} | {see or '—'} |"
        )
    lines.append("")
    return "\n".join(lines)


def validate(docs: list[Doc]) -> list[str]:
    problems: list[str] = []
    schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
    required = schema["required"]
    known = set(required) | {"supersedes", "superseded_by"}
    for doc in docs:
        where = doc.rel
        for field in required:
            if field not in doc.meta:
                problems.append(f"{where}: нет поля {field}")
        unknown = set(doc.meta) - known
        if unknown:
            problems.append(f"{where}: неизвестные поля {sorted(unknown)}")
        if doc.meta.get("kind") not in KIND_ORDER:
            problems.append(f"{where}: неизвестный kind {doc.meta.get('kind')!r}")
        if doc.meta.get("status") not in STATUSES:
            problems.append(f"{where}: неизвестный status {doc.meta.get('status')!r}")
        if doc.meta.get("status") == "заменено" and not doc.meta.get("superseded_by"):
            problems.append(f"{where}: status «заменено» без superseded_by")
        try:
            dt.date.fromisoformat(str(doc.meta.get("last_verified")))
        except ValueError:
            problems.append(f"{where}: last_verified не дата")
        summary = str(doc.meta.get("summary", ""))
        if len(summary) > 180:
            problems.append(f"{where}: summary длиннее 180 символов")
        body = doc.path.read_text(encoding="utf-8")
        if not H1.search(body):
            problems.append(f"{where}: нет заголовка H1")
    return problems


def staleness(docs: list[Doc]) -> list[str]:
    """Дату сверки ставит человек, поэтому проверяем и возраст, и правки после неё."""
    changed = set(
        subprocess.run(  # noqa: S603 - fixed argv, partial path to the developer's git
            ["git", "log", "--name-only", "--pretty=format:", "--since", f"{STALE_DAYS} days ago"],  # noqa: S607 - the developer's git is the point
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.split()
    )
    today = dt.datetime.now(dt.UTC).date()
    out: list[str] = []
    for doc in docs:
        try:
            seen = dt.date.fromisoformat(str(doc.meta["last_verified"]))
        except (KeyError, ValueError):
            continue
        age = (today - seen).days
        if age <= STALE_DAYS:
            continue
        note = f"{doc.rel}: проверен {age} дн. назад"
        if doc.rel in changed:
            note += ", файл менялся после проверки"
        out.append(note)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    args = parser.parse_args()

    docs = documents()
    problems = validate(docs)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1

    index = render_index(docs)
    glossary = render_glossary()
    if args.write:
        INDEX.write_text(index, encoding="utf-8")
        GLOSSARY_MD.write_text(glossary, encoding="utf-8")
        print(f"docs-index: {len(docs)} документов")
        return 0

    for path, expected in ((INDEX, index), (GLOSSARY_MD, glossary)):
        actual = path.read_text(encoding="utf-8") if path.exists() else ""
        if actual != expected:
            print(
                f"{path.relative_to(ROOT)}: индекс устарел, запустить make docs-index",
                file=sys.stderr,
            )
            return 1
    for line in staleness(docs):
        print(f"предупреждение: {line}", file=sys.stderr)
    print(f"docs-index ok: {len(docs)} документов")
    return 0


if __name__ == "__main__":
    sys.exit(main())
