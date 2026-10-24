"""Run the golden set against the configured database and provider.

Retrieval-only mode is deterministic and needs no model key. Full mode adds generation,
citation support, escalation correctness, latency, and cost. Every run writes two artifacts: the
Markdown measurement and a JSONL file with one line per case, because a comparison needs the
cases, not the averages.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from onboarding.app.container import build_container
from onboarding.app.llm.profiles import answer_profile, embedding_profile, rerank_profile
from onboarding.app.settings import Settings
from onboarding.evals.artifact import commit_hash
from onboarding.evals.runner import (
    Case,
    GoldenSetError,
    Report,
    baseline_json,
    baseline_refusal,
    case_record,
    compare_records,
    derive_baseline,
    evaluate,
    load_baseline,
    load_cases,
    load_jsonl,
    render_comparison,
    render_markdown,
    summarise,
    write_jsonl,
)
from onboarding.evals.stats import PairedDelta
from onboarding.ports import SearchQuery

ROOT = Path(__file__).resolve().parents[4]
BASELINE = ROOT / "docs" / "evals" / "baseline.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="onboarding.evals")
    parser.add_argument("--golden", type=Path, default=ROOT / "docs" / "evals" / "golden.yaml")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "docs" / "measurements")
    parser.add_argument("--retrieval-only", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="run only the first N cases")
    parser.add_argument(
        "--only",
        default="",
        help="comma-separated case ids; iterate on a fix without paying for the whole set",
    )
    parser.add_argument("--write", action="store_true", help="write a measurement file")
    parser.add_argument("--label", default="", help="suffix for the measurement file name")
    parser.add_argument("--note", default="", help="caveat to record in the measurement file")
    parser.add_argument(
        "--baseline",
        type=Path,
        default=BASELINE,
        help="pinned gates; derived from a known-good run with --write-baseline",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="pin this run as the baseline: gate = Wilson lower bound of what it measured",
    )
    parser.add_argument(
        "--force-baseline",
        action="store_true",
        help="pin even a failing run; the pinned gates then describe the failure",
    )
    parser.add_argument(
        "--compare",
        type=Path,
        default=None,
        help="JSONL artifact of an earlier run; reports a paired bootstrap against it",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="exit non-zero when a compared metric regressed with the interval excluding zero",
    )
    args = parser.parse_args(argv)

    try:
        cases = load_cases(args.golden)
    except GoldenSetError as error:
        print(f"golden set error: {error}", file=sys.stderr)
        return 2
    if args.limit:
        cases = cases[: args.limit]
    if args.only:
        wanted = [token.strip() for token in args.only.split(",") if token.strip()]
        known = {case.id for case in cases}
        unknown = [case_id for case_id in wanted if case_id not in known]
        if unknown:
            print(f"unknown case ids: {', '.join(unknown)}", file=sys.stderr)
            return 2
        cases = tuple(case for case in cases if case.id in set(wanted))
    return asyncio.run(_run(args, cases))


async def _run(args: argparse.Namespace, cases: tuple[Case, ...]) -> int:
    settings = Settings()
    generated = not args.retrieval_only
    if generated and not settings.is_llm_configured:
        print("LLM_API_KEY is not set; pass --retrieval-only", file=sys.stderr)
        return 2

    baseline = load_baseline(args.baseline) if args.baseline else None
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

    report = summarise(results, generated=generated, baseline=baseline)
    print(_console_table(report))
    print(_console_strata(report))

    comparison: tuple[PairedDelta, ...] = ()
    if args.compare is not None:
        comparison = _compare(args.compare, report)
        print("\ncomparison against " + str(args.compare))
        print(render_comparison(comparison))

    if args.write:
        _write(report, args, settings, on_date, comparison)
    if args.write_baseline:
        refusal = None if args.force_baseline else baseline_refusal(report)
        if refusal is not None:
            print(f"not pinning: {refusal}", file=sys.stderr)
            return 1
        pinned = derive_baseline(report, commit=commit_hash())
        args.baseline.parent.mkdir(parents=True, exist_ok=True)
        args.baseline.write_text(baseline_json(pinned), encoding="utf-8")
        print(f"wrote baseline {args.baseline} (commit {pinned.commit})")
    if args.fail_on_regression and any(delta.regression for delta in comparison):
        return 1
    return 1 if report.failures else 0


def _compare(path: Path, report: Report) -> tuple[PairedDelta, ...]:
    try:
        earlier = load_jsonl(path)
    except (OSError, GoldenSetError) as error:
        print(f"cannot compare: {error}", file=sys.stderr)
        return ()
    current = {result.case.id: case_record(result) for result in report.results}
    return compare_records(current, earlier)


def _console_table(report: Report) -> str:
    lines = [f"{'metric':<24}{'value':>10}", "-" * 34]
    for name, value in report.metrics.items():
        lines.append(f"{name:<24}{value:>10.3f}")
    if report.failures:
        lines.append(f"{'FAILED':<24}{', '.join(report.failures)}")
    else:
        lines.append(f"{'status':<24}{'PASS':>10}")
    return "\n".join(lines)


def _console_strata(report: Report) -> str:
    if not report.strata:
        return ""
    lines = [
        "",
        f"{'stratum':<14}{'cases':>7}{'recall':>9}{'escal':>8}{'contains':>10}",
    ]
    for stratum, metrics in report.strata.items():
        lines.append(
            f"{stratum:<14}{report.counts[stratum]:>7}"
            f"{_cell(metrics.get('recall_at_5'), 9)}"
            f"{_cell(metrics.get('escalation_correctness'), 8)}"
            f"{_cell(metrics.get('answer_contains'), 10)}"
        )
    return "\n".join(lines)


def _cell(value: float | None, width: int) -> str:
    return f"{'-':>{width}}" if value is None else f"{value:>{width}.2f}"


def _write(
    report: Report,
    args: argparse.Namespace,
    settings: Settings,
    on_date: date,
    comparison: tuple[PairedDelta, ...] = (),
) -> None:
    args.out_dir.mkdir(parents=True, exist_ok=True)
    scope = "retrieval" if args.retrieval_only else "full"
    suffix = f"-{args.label}" if args.label else ""
    stem = f"{on_date.isoformat()}-eval-{scope}{suffix}"
    path = args.out_dir / f"{stem}.md"
    artifact = args.out_dir / f"{stem}.jsonl"
    write_jsonl(report, artifact)
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
            commit=commit_hash(),
            model=_model_label(settings, retrieval_only=args.retrieval_only),
            environment=settings.environment,
            embed_provider=settings.embed_provider,
            note=note,
            on_date=on_date,
            retrieval=retrieval_label(settings),
            artifact=artifact.name,
            comparison=comparison,
        ),
        encoding="utf-8",
    )
    print(f"wrote {path}")
    print(f"wrote {artifact}")


def _model_label(settings: Settings, *, retrieval_only: bool) -> str:
    if retrieval_only:
        return "n/a"
    if settings.llm_provider == "extractive":
        return "extractive (offline)"
    profile = answer_profile(settings)
    return f"{settings.llm_provider}/{profile.name} ({profile.model}) @ {settings.llm_base_url}"


def retrieval_label(settings: Settings) -> str:
    """Everything that changes a retrieved list, in one line a later reader can diff.

    The embedder and the reranker were here first; ``bm25`` and contextual retrieval were not,
    which made two experiment arms produce the same header (ADR 0012, ADR 0016).
    """
    embed = embedding_profile(settings)
    rerank = rerank_profile(settings)
    ranking = f"{rerank.name} ({rerank.model})" if rerank is not None else "none"
    bm25 = "on" if settings.bm25_enabled else "off"
    contextual = (
        f"v{settings.contextual_prompt_version}" if settings.contextual_retrieval else "off"
    )
    return (
        f"{embed.name} ({embed.model}, dim {embed.dim}) + rerank:{ranking} "
        f"+ bm25:{bm25} + contextual:{contextual}"
    )


if __name__ == "__main__":
    sys.exit(main())
