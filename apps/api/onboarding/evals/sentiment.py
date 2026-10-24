"""Measure a sentiment classifier against the labeled survey answers.

The answer evals prove grounding; this one proves the risk radar. Three providers share the same
cases: the deterministic keyword classifier, the versioned chat prompt, and the Jev rubric. A
provider that is not configured is skipped with a clear message, never silently scored as zero.

The report is built for decisions, not for a demo:

- every share carries a Wilson 95% interval, because "0.88" on a handful of cases is not a number;
- tones are scored with macro F1 and a confusion matrix, so a rare class cannot hide behind
  accuracy;
- escalation is scored against ``core/risk.py``, the code that actually decides, so a missed
  crisis is visible as a product failure and not only as a wrong label;
- every run writes machine-readable JSONL next to the table, and ``--compare`` runs a paired
  bootstrap against an earlier run, because two accuracies without a difference interval are a
  coin flip;
- ``--repeat`` calls the provider more than once per case and names the cases whose verdict is not
  stable, so a non-deterministic model is not mistaken for a precise one.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn

import httpx

from onboarding.app.clock import SystemClock
from onboarding.app.llm.gateway import build_llm
from onboarding.app.llm.sentiment import SentimentChoice, SentimentSetupError, build_sentiment
from onboarding.app.prompts import PromptLibrary
from onboarding.app.settings import Settings

# ``Case``, ``load_cases`` and ``SentimentSetError`` stay importable from here: the module is the
# eval's public surface even when the loader lives next door.
from onboarding.evals.sentiment_cases import (
    DEFAULT_CASES,
    SPLITS,
    Case,
    SentimentSetError,
    load_cases,
)
from onboarding.evals.sentiment_metrics import (
    CaseResult,
    Comparison,
    Report,
    compare_reports,
    degraded_beyond,
    load_artifact,
)
from onboarding.evals.sentiment_report import render_artifact, render_markdown
from onboarding.ports import AuditLog, SentimentAnalysis

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_OUT = ROOT / "docs" / "measurements"
# The provider is the class of model, not a vendor (ADR 0029). ``jev`` is the name the first
# artifacts used; it still resolves so an old command in a measurement file keeps running, but every
# new artifact records ``decisions``.
PROVIDERS = ("keyword", "prompt", "decisions", "jev")
ALIASES = {"jev": "decisions"}
Z_95 = 1.959963984540054
BOOTSTRAP_ROUNDS = 5000
BOOTSTRAP_SEED = 20261023
# A degraded provider is an outage, not a model quality result. Above this share, refuse the run.
MAX_FALLBACK_RATE = 0.10


class CountingAudit:
    """Count what the classifier did to itself, so a fallback is visible in the report.

    It also sums the spend the classifier reported, because a classifier that is better but
    unaffordable is not an improvement, and a price nobody measured is a guess.
    """

    def __init__(self) -> None:
        self.fallbacks = 0
        self.format_errors = 0
        self.reasons: Counter[str] = Counter()
        self.input_tokens = 0
        self.output_tokens = 0
        self.cost_rub = 0.0
        self.cost_usd = 0.0
        self.priced_calls = 0

    async def record(self, name: str, **fields: Any) -> None:
        if name == "sentiment_classified":
            tokens = fields.get("input_tokens")
            cost = fields.get("cost_rub")
            if isinstance(tokens, int) and not isinstance(tokens, bool):
                self.input_tokens += tokens
            if isinstance(cost, int | float) and not isinstance(cost, bool):
                self.cost_rub += float(cost)
            charged = fields.get("cost_usd")
            if isinstance(charged, int | float) and not isinstance(charged, bool):
                self.cost_usd += float(charged)
                self.priced_calls += 1
        if name == "sentiment_fallback":
            self.fallbacks += 1
            reason = fields.get("reason")
            if isinstance(reason, str):
                self.reasons[reason] += 1
        if name == "sentiment_format_error":
            self.format_errors += 1


async def evaluate(
    cases: tuple[Case, ...],
    classifier: SentimentAnalysis,
    *,
    provider: str,
    audit: CountingAudit,
    repeat: int = 1,
    split: str = "all",
    min_interval_s: float = 0.0,
    identity: SentimentChoice | None = None,
) -> Report:
    results: list[CaseResult] = []
    for rep in range(repeat):
        for index, case in enumerate(cases):
            if min_interval_s > 0 and index:
                await asyncio.sleep(min_interval_s)
            started = time.perf_counter()
            signal = await classifier.classify(case.text, source=case.id)
            elapsed = (time.perf_counter() - started) * 1000
            results.append(CaseResult(case=case, signal=signal, latency_ms=elapsed, rep=rep))
    return Report(
        provider=provider,
        split=split,
        repeat=repeat,
        results=tuple(results),
        fallbacks=audit.fallbacks,
        format_errors=audit.format_errors,
        fallback_reasons=tuple(sorted(audit.reasons.items())),
        model=identity.model if identity else "",
        rubric=identity.rubric if identity else "",
        prompt_version=identity.prompt_version if identity else None,
        input_tokens=audit.input_tokens,
        output_tokens=audit.output_tokens,
        cost_rub=audit.cost_rub,
        cost_usd=audit.cost_usd,
        priced_calls=audit.priced_calls,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="onboarding.evals.sentiment")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--provider", choices=PROVIDERS, default="keyword")
    parser.add_argument("--split", choices=SPLITS, default="all")
    parser.add_argument("--repeat", type=int, default=1, help="calls per case, for stability")
    parser.add_argument(
        "--compare", type=Path, default=None, help="earlier JSONL artifact for a paired bootstrap"
    )
    parser.add_argument("--bootstrap", type=int, default=BOOTSTRAP_ROUNDS)
    parser.add_argument(
        "--from-artifact",
        type=Path,
        default=None,
        help="re-render an earlier JSONL run without calling a provider, e.g. after a metric fix",
    )
    parser.add_argument(
        "--min-interval",
        type=float,
        default=0.0,
        help="seconds to wait between calls, for a rate-limited provider",
    )
    parser.add_argument(
        "--max-fallback-rate",
        type=float,
        default=MAX_FALLBACK_RATE,
        help="abort when more calls than this degraded to keywords; 0 for a no-quality run",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--label", default="")
    parser.add_argument("--note", default="")
    args = parser.parse_args(argv)
    return asyncio.run(_run(args))


def _command_line(args: argparse.Namespace) -> str:
    parts = [
        "python -m onboarding.evals.sentiment",
        f"--provider {canonical_provider(args.provider)}",
        f"--split {args.split}",
        f"--repeat {args.repeat}",
    ]
    if args.min_interval:
        parts.append(f"--min-interval {args.min_interval}")
    if args.compare:
        parts.append(f"--compare {args.compare}")
    return " ".join(parts)


class _EvalAbortError(Exception):
    """A run that must not produce a number. Carries the process exit code."""

    def __init__(self, code: int) -> None:
        super().__init__(code)
        self.code = code


def _abort(code: int, message: str) -> NoReturn:
    print(message, file=sys.stderr)
    raise _EvalAbortError(code)


def canonical_provider(name: str) -> str:
    """The class name an artifact records, whichever spelling the command used."""
    return ALIASES.get(name, name)


def _build(
    provider: str, settings: Settings, http: httpx.AsyncClient, audit: AuditLog
) -> SentimentChoice:
    try:
        return build_sentiment(
            settings,
            clock=SystemClock(),
            client=http,
            prompts=PromptLibrary(settings.prompts_dir),
            audit=audit,
            llm=build_llm(settings, SystemClock(), http),
            provider=provider,
        )
    except SentimentSetupError as error:
        raise SentimentSetError(str(error)) from None


async def _measure(args: argparse.Namespace, cases: tuple[Case, ...]) -> Report:
    if args.repeat < 1:
        _abort(2, "--repeat must be at least 1")
    if args.from_artifact is not None:
        try:
            return load_artifact(args.from_artifact)
        except SentimentSetError as error:
            _abort(2, str(error))
    audit = CountingAudit()
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0)) as http:
        try:
            choice = _build(canonical_provider(args.provider), Settings(), http, audit)
        except SentimentSetError as error:
            _abort(2, str(error))
        return await evaluate(
            cases,
            choice.classifier,
            provider=canonical_provider(args.provider),
            audit=audit,
            repeat=args.repeat,
            split=args.split,
            min_interval_s=args.min_interval,
            identity=choice,
        )


async def _run(args: argparse.Namespace) -> int:
    try:
        return await _run_inner(args)
    except _EvalAbortError as error:
        return error.code


async def _run_inner(args: argparse.Namespace) -> int:
    try:
        cases = load_cases(args.cases, split=args.split)
    except SentimentSetError as error:
        _abort(2, f"sentiment set error: {error}")
    report = await _measure(args, cases)
    if report.fallbacks or report.format_errors:
        reasons = ", ".join(f"{reason}={count}" for reason, count in report.fallback_reasons)
        print(
            f"warnings: {report.fallbacks} fallbacks ({reasons or 'no reason'}), "
            f"{report.format_errors} format errors",
            file=sys.stderr,
        )
    if report.provider != "keyword" and degraded_beyond(report, args.max_fallback_rate):
        _abort(
            3,
            f"refusing to report: {report.infra_fallback_rate:.0%} of calls degraded to keywords "
            f"because the provider was unavailable (limit {args.max_fallback_rate:.0%}). "
            "The provider is down or rate-limited, so these numbers measure the network, "
            "not the model. Rerun with a pause: --min-interval 0.5",
        )
    comparison: Comparison | None = None
    if args.compare is not None:
        try:
            baseline = load_artifact(args.compare)
        except SentimentSetError as error:
            _abort(2, str(error))
        comparison = compare_reports(baseline, report, rounds=args.bootstrap)
    command = _command_line(args)
    markdown = render_markdown(report, command=command, note=args.note, comparison=comparison)
    print(markdown)
    if args.write:
        suffix = f"-{args.label}" if args.label else ""
        stem = f"{datetime.now(UTC):%Y-%m-%d}-sentiment-{report.provider}{suffix}"
        path = args.out_dir / f"{stem}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown + "\n", encoding="utf-8")
        artifact = args.out_dir / f"{stem}.jsonl"
        artifact.write_text(render_artifact(report, command=command), encoding="utf-8")
        print(f"wrote {path} and {artifact}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
