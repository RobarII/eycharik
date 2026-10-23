"""Operator commands: index the corpus, seed employees, inspect settings.

Run as ``uv run python -m onboarding.cli <command>``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert

from onboarding.app.container import build_container
from onboarding.app.db.kb import PostgresKnowledgeWriter
from onboarding.app.db.models import EmployeeRow
from onboarding.app.knowledge.pipeline import ingest
from onboarding.app.settings import Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="onboarding")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest_parser = sub.add_parser("ingest", help="index the knowledge corpus")
    ingest_parser.add_argument("--dir", type=Path, default=None)
    ingest_parser.add_argument("--max-chars", type=int, default=1200)
    ingest_parser.add_argument("--overlap-chars", type=int, default=200)

    seed_parser = sub.add_parser("seed", help="load employees from a JSON file")
    seed_parser.add_argument("--file", type=Path, required=True)

    sub.add_parser("check", help="validate settings and scenario files")

    args = parser.parse_args(argv)
    settings = Settings()
    if args.command == "ingest":
        return asyncio.run(_ingest(settings, args))
    if args.command == "seed":
        return asyncio.run(_seed(settings, args.file))
    return _check(settings)


async def _ingest(settings: Settings, args: argparse.Namespace) -> int:
    container = build_container(settings)
    try:
        report = await ingest(
            directory=args.dir or settings.knowledge_dir,
            schema_path=settings.contracts_dir / "doc.schema.json",
            writer=PostgresKnowledgeWriter(container.database),
            embedder=container.embedder,
            max_chars=args.max_chars,
            overlap_chars=args.overlap_chars,
        )
    finally:
        await container.aclose()
    print(f"indexed {report.documents} documents, {report.chunks} chunks")
    return 0


async def _seed(settings: Settings, path: Path) -> int:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit(f"{path}: expected a list of employees")
    rows = [_employee_row(item) for item in raw]
    container = build_container(settings)
    try:
        statement = insert(EmployeeRow).values(rows)
        async with container.database.session() as session:
            await session.execute(
                statement.on_conflict_do_update(
                    index_elements=[EmployeeRow.id],
                    set_={
                        "name": statement.excluded.name,
                        "role": statement.excluded.role,
                        "department": statement.excluded.department,
                        "recruiter_id": statement.excluded.recruiter_id,
                        "started_at": statement.excluded.started_at,
                        "audience": statement.excluded.audience,
                    },
                )
            )
    finally:
        await container.aclose()
    print(f"seeded {len(rows)} employees")
    return 0


def _employee_row(item: object) -> dict[str, object]:
    if not isinstance(item, dict):
        raise SystemExit("each employee must be an object")
    return {
        "id": str(item["id"]),
        "name": str(item["name"]),
        "role": str(item["role"]),
        "department": str(item["department"]),
        "recruiter_id": str(item["recruiter_id"]),
        "started_at": date.fromisoformat(str(item["started_at"])),
        "audience": [str(value) for value in item["audience"]],
    }


def _check(settings: Settings) -> int:

    container = build_container(settings)
    try:
        print(f"scenarios: {', '.join(container.catalog.ids())}")
        print(f"prompts: {settings.prompts_dir}")
        print(f"knowledge: {settings.knowledge_dir}")
    finally:
        asyncio.run(container.aclose())
    return 0


if __name__ == "__main__":
    sys.exit(main())
