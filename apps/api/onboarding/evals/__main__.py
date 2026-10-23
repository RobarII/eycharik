"""Run the golden set against the configured database and provider.

Retrieval-only mode is deterministic and needs no model key. Full mode adds generation,
citation support, escalation correctness, latency, and cost.
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from onboarding.app.container import build_container
from onboarding.app.settings import Settings
from onboarding.evals.runner import (
    Case,
    GoldenSetError,
    Report,
    evaluate,
    load_cases,
    render_markdown,
    summarise,
)
from onboarding.ports import SearchQuery

ROOT = Path(__file__).resolve().parents[4]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="onboarding.evals")
    parser.add_argument("--golden", type=Path, default=ROOT / "docs" / "evals" / "golden.yaml")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "docs" / "measurements")
    parser.add_argument("--retrieval-only", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="run only the first N cases")
    parser.add_argument("--write", action="store_true", help="write a measurement file")
    parser.add_argument("--label", default="", help="suffix for the measurement file name")
    args = parser.parse_args(argv)

    try:
        cases = load_cases(args.golden)
    except GoldenSetError as error:
        print(f"golden set error: {error}", file=sys.stderr)
        return 2
    if args.limit:
        cases = cases[: args.limit]
    return asyncio.run(_run(args, cases))


async def _run(args: argparse.Namespace, cases: tuple[Case, ...]) -> int:
    settings = Settings()
    generated = not args.retrieval_only
    if generated and not settings.is_llm_configured:
        print("LLM_API_KEY is not set; pass --retrieval-only", file=sys.stderr)
        return 2

    on_date = datetime.now(UTC).date()
    container = build_container(settings)
    try:
        probe = await container.knowledge.search(
            SearchQuery(
                text=cases[0].question,
                audience=("all",),
                on_date=on_date,
                limit=5,
            )
        )
        if not probe:
            print("knowledge base is empty; run `make ingest` first", file=sys.stderr)
            return 2
        results = await evaluate(
            cases,
            knowledge=container.knowledge,
            answerer=None if args.retrieval_only else container.answerer,
            on_date=on_date,
        )
    finally:
        await container.aclose()

    report = summarise(results, generated=generated)
    print(_console_table(report))
    if args.write:
        _write(report, args, settings, on_date)
    return 1 if report.failures else 0


def _console_table(report: Report) -> str:
    lines = [f"{'metric':<24}{'value':>10}", "-" * 34]
    for name, value in report.metrics.items():
        lines.append(f"{name:<24}{value:>10.3f}")
    if report.failures:
        lines.append(f"{'FAILED':<24}{', '.join(report.failures)}")
    else:
        lines.append(f"{'status':<24}{'PASS':>10}")
    return "\n".join(lines)


def _write(
    report: Report, args: argparse.Namespace, settings: Settings, on_date: date
) -> None:
    args.out_dir.mkdir(parents=True, exist_ok=True)
    scope = "retrieval" if args.retrieval_only else "full"
    suffix = f"-{args.label}" if args.label else ""
    path = args.out_dir / f"{on_date.isoformat()}-eval-{scope}{suffix}.md"
    command = "python -m onboarding.evals"
    if args.retrieval_only:
        command += " --retrieval-only"
    path.write_text(
        render_markdown(
            report,
            command=command,
            commit=_commit(),
            model="n/a" if args.retrieval_only else settings.llm_model,
            environment=settings.environment,
            on_date=on_date,
        ),
        encoding="utf-8",
    )
    print(f"wrote {path}")


def _commit() -> str:
    git = shutil.which("git")
    if git is None:
        return "unknown"
    try:
        return subprocess.run(  # noqa: S603 - resolved binary, fixed argv, no shell
            [git, "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


if __name__ == "__main__":
    sys.exit(main())
