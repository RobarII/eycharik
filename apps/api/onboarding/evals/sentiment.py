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
import json
import math
import random
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn

import httpx

from onboarding.app.clock import SystemClock
from onboarding.app.llm.gateway import build_llm
from onboarding.app.llm.sentiment import SentimentChoice, SentimentSetupError, build_sentiment
from onboarding.app.prompts import PromptLibrary
from onboarding.app.settings import Settings
from onboarding.core.models import RiskLevel, RiskSignal, Sentiment, SignalTag
from onboarding.core.risk import assess

# ``Case``, ``load_cases`` and ``SentimentSetError`` stay importable from here: the module is the
# eval's public surface even when the loader lives next door.
from onboarding.evals.sentiment_cases import (
    DEFAULT_CASES,
    SPLITS,
    Case,
    SentimentSetError,
    load_cases,
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


@dataclass(frozen=True, slots=True)
class CaseResult:
    case: Case
    signal: RiskSignal
    latency_ms: float
    rep: int = 0

    @property
    def sentiment_ok(self) -> bool:
        return self.signal.sentiment is self.case.sentiment

    @property
    def level_escalates(self) -> bool:
        assessment = assess((self.signal,))
        return assessment.level is RiskLevel.HIGH and assessment.escalate_to == "recruiter"

    @property
    def matched_tags(self) -> tuple[SignalTag, ...]:
        return tuple(tag for tag in self.case.tags if tag in self.signal.tags)


@dataclass(frozen=True, slots=True)
class Interval:
    low: float
    high: float

    def render(self) -> str:
        return f"[{self.low:.2f}, {self.high:.2f}]"


@dataclass(frozen=True, slots=True)
class Comparison:
    """One paired bootstrap between two runs of the same set."""

    metric: str
    baseline: float
    candidate: float
    delta: float
    interval: Interval
    p_value: float
    paired_cases: int


@dataclass(frozen=True, slots=True)
class Report:
    provider: str
    split: str
    repeat: int
    results: tuple[CaseResult, ...]
    fallbacks: int
    format_errors: int
    fallback_reasons: tuple[tuple[str, int], ...] = ()
    # What ran: a measurement without a model and a prompt version is an anecdote.
    model: str = ""
    rubric: str = ""
    prompt_version: int | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_rub: float = 0.0
    cost_usd: float = 0.0
    priced_calls: int = 0

    @property
    def cases(self) -> tuple[Case, ...]:
        return tuple(dict.fromkeys(result.case for result in self.results))

    @property
    def sentiment_accuracy(self) -> float:
        return _ratio(sum(result.sentiment_ok for result in self.results), len(self.results))

    @property
    def sentiment_accuracy_ci(self) -> Interval:
        return _wilson(self.sentiment_accuracy, len(self.results))

    @property
    def per_class_recall(self) -> dict[Sentiment, float]:
        recalls: dict[Sentiment, float] = {}
        for sentiment in Sentiment:
            cases = [result for result in self.results if result.case.sentiment is sentiment]
            if cases:
                hits = sum(result.sentiment_ok for result in cases)
                recalls[sentiment] = _ratio(hits, len(cases))
        return recalls

    @property
    def confusion(self) -> dict[tuple[Sentiment, Sentiment], int]:
        matrix: dict[tuple[Sentiment, Sentiment], int] = {}
        for result in self.results:
            key = (result.case.sentiment, result.signal.sentiment)
            matrix[key] = matrix.get(key, 0) + 1
        return matrix

    @property
    def case_verdicts(self) -> dict[str, Sentiment]:
        """One verdict per case: the majority over repetitions, first rep on a tie."""
        votes: dict[str, list[Sentiment]] = {}
        for result in self.results:
            votes.setdefault(result.case.id, []).append(result.signal.sentiment)
        verdicts: dict[str, Sentiment] = {}
        for case_id, seen in votes.items():
            best = Counter(seen).most_common()
            tied = len(best) > 1 and best[0][1] == best[1][1]
            verdicts[case_id] = seen[0] if tied else best[0][0]
        return verdicts

    @property
    def case_accuracy(self) -> float:
        verdicts = self.case_verdicts
        expected = {result.case.id: result.case.sentiment for result in self.results}
        hits = sum(verdicts[case_id] is sentiment for case_id, sentiment in expected.items())
        return _ratio(hits, len(expected))

    @property
    def macro_f1(self) -> float:
        scores: list[float] = []
        for sentiment in Sentiment:
            expected = [result for result in self.results if result.case.sentiment is sentiment]
            predicted = [result for result in self.results if result.signal.sentiment is sentiment]
            if not expected and not predicted:
                continue
            hits = sum(
                1
                for result in self.results
                if result.case.sentiment is sentiment and result.signal.sentiment is sentiment
            )
            precision = _ratio(hits, len(predicted))
            recall = _ratio(hits, len(expected))
            scores.append(_f1(precision, recall))
        return _ratio(sum(scores), len(scores))

    @property
    def tag_precision(self) -> float:
        matched = sum(len(result.matched_tags) for result in self.results)
        predicted = sum(len(result.signal.tags) for result in self.results)
        return _ratio(matched, predicted)

    @property
    def tag_recall(self) -> float:
        matched = sum(len(result.matched_tags) for result in self.results)
        expected = sum(len(result.case.tags) for result in self.results)
        return _ratio(matched, expected)

    @property
    def tag_f1(self) -> float:
        return _f1(self.tag_precision, self.tag_recall)

    @property
    def per_tag_recall(self) -> dict[SignalTag, float]:
        recalls: dict[SignalTag, float] = {}
        for tag in SignalTag:
            cases = [result for result in self.results if tag in result.case.tags]
            if cases:
                recalls[tag] = _ratio(
                    sum(tag in result.signal.tags for result in cases), len(cases)
                )
        return recalls

    @property
    def escalation_cases(self) -> tuple[CaseResult, ...]:
        return tuple(result for result in self.results if result.case.expect_escalation)

    @property
    def escalation_recall(self) -> float:
        cases = self.escalation_cases
        return _ratio(sum(result.level_escalates for result in cases), len(cases))

    @property
    def escalation_recall_ci(self) -> Interval:
        cases = self.escalation_cases
        return _wilson(self.escalation_recall, len(cases))

    @property
    def false_alarm_rate(self) -> float:
        cases = [result for result in self.results if not result.case.expect_escalation]
        return _ratio(sum(result.level_escalates for result in cases), len(cases))

    @property
    def fallback_rate(self) -> float:
        return _ratio(self.fallbacks, len(self.results))

    @property
    def format_fallbacks(self) -> int:
        return dict(self.fallback_reasons).get("format", 0)

    @property
    def infra_fallbacks(self) -> int:
        return self.fallbacks - self.format_fallbacks

    @property
    def infra_fallback_rate(self) -> float:
        return _ratio(self.infra_fallbacks, len(self.results))

    @property
    def format_error_rate(self) -> float:
        return _ratio(self.format_errors, len(self.results))

    @property
    def cost_per_1k_calls(self) -> float:
        """What a thousand labels would cost at this run's measured spend, not at a sticker."""
        return self.cost_rub / len(self.results) * 1000 if self.results else 0.0

    @property
    def cost_usd_per_1k_calls(self) -> float:
        """What the provider actually charged, scaled. Zero until a priced call appears."""
        return self.cost_usd / len(self.results) * 1000 if self.results else 0.0

    @property
    def p50_latency_ms(self) -> float:
        return _percentile([result.latency_ms for result in self.results], 0.50)

    @property
    def p95_latency_ms(self) -> float:
        return _percentile([result.latency_ms for result in self.results], 0.95)

    @property
    def p99_latency_ms(self) -> float:
        return _percentile([result.latency_ms for result in self.results], 0.99)

    @property
    def flaky_cases(self) -> tuple[str, ...]:
        """Cases whose verdict changed between repetitions. Stable input, unstable answer."""
        by_case: dict[str, set[Sentiment]] = {}
        for result in self.results:
            by_case.setdefault(result.case.id, set()).add(result.signal.sentiment)
        return tuple(sorted(case_id for case_id, seen in by_case.items() if len(seen) > 1))

    @property
    def failures(self) -> tuple[CaseResult, ...]:
        verdicts = self.case_verdicts
        broken = [
            result
            for result in self.results
            if verdicts[result.case.id] is not result.case.sentiment
            or len(result.matched_tags) < len(result.case.tags)
        ]
        return _one_per_case(broken)

    @property
    def missed_escalations(self) -> tuple[CaseResult, ...]:
        return _one_per_case(
            [result for result in self.escalation_cases if not result.level_escalates]
        )


def degraded_beyond(report: Report, limit: float) -> bool:
    """A run is unusable when the provider, not the model, decided most of the verdicts.

    A malformed answer is a model failure and belongs in the table. An unavailable provider is an
    outage: every call after it degrades to keywords, and the numbers stop describing the model.
    """
    return report.infra_fallback_rate > limit


def _wilson(share: float, total: int, z: float = Z_95) -> Interval:
    """Wilson score interval: honest even when the share is near 0 or 1, and at small n."""
    if total <= 0:
        return Interval(0.0, 1.0)
    denominator = 1.0 + z * z / total
    centre = (share + z * z / (2.0 * total)) / denominator
    spread = z * math.sqrt(share * (1.0 - share) / total + z * z / (4.0 * total * total))
    low = max(0.0, centre - spread / denominator)
    high = min(1.0, centre + spread / denominator)
    return Interval(low, high)


def _f1(precision: float, recall: float) -> float:
    return 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0


def _one_per_case(results: list[CaseResult]) -> tuple[CaseResult, ...]:
    """A repeated run fails the same case once; a table with duplicates hides the count."""
    seen: set[str] = set()
    unique: list[CaseResult] = []
    for result in results:
        if result.case.id in seen:
            continue
        seen.add(result.case.id)
        unique.append(result)
    return tuple(unique)


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1)
    return ordered[index]


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


def _correctness(report: Report) -> dict[str, bool]:
    """One boolean per case id, repetitions collapsed to a majority where they disagree."""
    votes: dict[str, list[bool]] = {}
    for result in report.results:
        votes.setdefault(result.case.id, []).append(result.sentiment_ok)
    return {case_id: sum(values) * 2 >= len(values) for case_id, values in votes.items()}


def compare_reports(
    baseline: Report,
    candidate: Report,
    *,
    rounds: int = BOOTSTRAP_ROUNDS,
    seed: int = BOOTSTRAP_SEED,
) -> Comparison | None:
    """Paired bootstrap over cases both runs scored.

    Unpaired comparison of two accuracies on different samples is how people talk themselves into a
    regression. Same cases, resampled together, is the cheapest honest test.
    """
    base = _correctness(baseline)
    cand = _correctness(candidate)
    shared = sorted(base.keys() & cand.keys())
    if not shared:
        return None
    base_hits = [base[case_id] for case_id in shared]
    cand_hits = [cand[case_id] for case_id in shared]
    baseline_score = _ratio(sum(base_hits), len(shared))
    candidate_score = _ratio(sum(cand_hits), len(shared))
    generator = random.Random(seed)  # noqa: S311 - a fixed seed for a bootstrap, not a secret
    deltas: list[float] = []
    for _ in range(rounds):
        picked = [generator.randrange(len(shared)) for _ in range(len(shared))]
        base_rate = _ratio(sum(base_hits[index] for index in picked), len(picked))
        cand_rate = _ratio(sum(cand_hits[index] for index in picked), len(picked))
        deltas.append(cand_rate - base_rate)
    deltas.sort()
    return Comparison(
        metric="case_accuracy",
        baseline=baseline_score,
        candidate=candidate_score,
        delta=candidate_score - baseline_score,
        interval=Interval(
            deltas[max(0, int(0.025 * rounds) - 1)],
            deltas[min(rounds - 1, int(0.975 * rounds))],
        ),
        p_value=_ratio(sum(delta <= 0 for delta in deltas), rounds),
        paired_cases=len(shared),
    )


def load_artifact(path: Path) -> Report:
    """Read a run written by ``--write``. No model, no network: the comparison is free."""
    if not path.is_file():
        raise SentimentSetError(f"missing artifact {path}")
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    header = next((line for line in lines if line.get("kind") == "run"), None)
    if header is None:
        raise SentimentSetError(f"{path}: no run header")
    results: list[CaseResult] = []
    for line in lines:
        if line.get("kind") != "case":
            continue
        try:
            case = Case(
                id=str(line["id"]),
                text="",
                sentiment=Sentiment(str(line["expected_sentiment"])),
                tags=tuple(SignalTag(tag) for tag in line["expected_tags"]),
                expect_escalation=bool(line.get("expect_escalation", False)),
            )
            signal = RiskSignal(
                source=case.id,
                sentiment=Sentiment(str(line["predicted_sentiment"])),
                tags=tuple(SignalTag(tag) for tag in line["predicted_tags"]),
                confidence=float(line["confidence"]),
            )
        except (KeyError, ValueError) as error:
            raise SentimentSetError(f"{path}: broken case line: {error}") from None
        results.append(
            CaseResult(
                case=case,
                signal=signal,
                latency_ms=float(line.get("latency_ms", 0.0)),
                rep=int(line.get("rep", 0)),
            )
        )
    return Report(
        provider=str(header.get("provider", "unknown")),
        split=str(header.get("split", "all")),
        repeat=int(header.get("repeat", 1)),
        results=tuple(results),
        fallbacks=int(header.get("fallbacks", 0)),
        format_errors=int(header.get("format_errors", 0)),
        fallback_reasons=tuple(
            (str(reason), int(count)) for reason, count in header.get("fallback_reasons", [])
        ),
        model=str(header.get("model") or ""),
        rubric=str(header.get("rubric") or ""),
        prompt_version=header.get("prompt_version"),
        input_tokens=int(header.get("input_tokens", 0)),
        output_tokens=int(header.get("output_tokens", 0)),
        cost_rub=float(header.get("cost_rub", 0.0)),
        cost_usd=float(header.get("cost_usd", 0.0)),
        priced_calls=int(header.get("priced_calls", 0)),
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
