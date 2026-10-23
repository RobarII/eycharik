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
from onboarding.app.llm.profiles import answer_profile, embedding_profile, rerank_profile
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
    parser.add_argument("--note", default="", help="caveat to record in the measurement file")
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


def _write(report: Report, args: argparse.Namespace, settings: Settings, on_date: date) -> None:
    args.out_dir.mkdir(parents=True, exist_ok=True)
    scope = "retrieval" if args.retrieval_only else "full"
    suffix = f"-{args.label}" if args.label else ""
    path = args.out_dir / f"{on_date.isoformat()}-eval-{scope}{suffix}.md"
    command = " ".join(["python -m onboarding.evals", *sys.argv[1:]]).strip()
    note = args.note.strip() or None
    if settings.llm_provider == "extractive":
        note = (
            "the offline extractive provider returns zero latency and cost by construction; "
            "this measures retrieval, grounding, and escalation, not model quality"
        )
    path.write_text(
        render_markdown(
            report,
            command=command,
            commit=_commit(),
            model=_model_label(settings, retrieval_only=args.retrieval_only),
            environment=settings.environment,
            embed_provider=settings.embed_provider,
            note=note,
            on_date=on_date,
            retrieval=_retrieval_label(settings),
        ),
        encoding="utf-8",
    )
    print(f"wrote {path}")


def _model_label(settings: Settings, *, retrieval_only: bool) -> str:
    if retrieval_only:
        return "n/a"
    if settings.llm_provider == "extractive":
        return "extractive (offline)"
    profile = answer_profile(settings)
    return f"{settings.llm_provider}/{profile.name} ({profile.model}) @ {settings.llm_base_url}"


def _retrieval_label(settings: Settings) -> str:
    embed = embedding_profile(settings)
    rerank = rerank_profile(settings)
    ranking = f"{rerank.name} ({rerank.model})" if rerank is not None else "none"
    return f"{embed.name} ({embed.model}, dim {embed.dim}) + rerank:{ranking}"


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
