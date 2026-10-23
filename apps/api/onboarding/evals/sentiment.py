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
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, NoReturn

import httpx
import yaml

from onboarding.app.clock import SystemClock
from onboarding.app.llm.gateway import build_llm
from onboarding.app.llm.jev import build_jev_classifier
from onboarding.app.llm.profiles import classify_profile
from onboarding.app.llm.rubric import RubricLibrary
from onboarding.app.llm.sentiment import PROMPT_VERSION, SentimentClassifier
from onboarding.app.prompts import PromptLibrary
from onboarding.app.settings import Settings
from onboarding.core.models import RiskLevel, RiskSignal, Sentiment, SignalTag
from onboarding.core.risk import assess, keyword_signal
from onboarding.ports import AuditLog, SentimentAnalysis

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CASES = ROOT / "docs" / "evals" / "sentiment.yaml"
DEFAULT_OUT = ROOT / "docs" / "measurements"
PROVIDERS = ("keyword", "prompt", "jev")
SPLITS = ("dev", "test", "all")
Z_95 = 1.959963984540054
BOOTSTRAP_ROUNDS = 5000
BOOTSTRAP_SEED = 20261023
SET_VERSION = 2
MAX_TAGS_PER_CASE = 3
# A degraded provider is an outage, not a model quality result. Above this share, refuse the run.
MAX_FALLBACK_RATE = 0.10


class SentimentSetError(ValueError):
    """The labeled set does not satisfy the schema this runner reads."""


@dataclass(frozen=True, slots=True)
class Case:
    id: str
    text: str
    sentiment: Sentiment
    tags: tuple[SignalTag, ...]
    split: Literal["dev", "test"] = "dev"
    expect_escalation: bool = False
    note: str = ""


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
            predicted = [
                result for result in self.results if result.signal.sentiment is sentiment
            ]
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


def load_cases(path: Path, *, split: str = "all") -> tuple[Case, ...]:
    if not path.is_file():
        raise SentimentSetError(f"missing sentiment set {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise SentimentSetError(f"{path}: expected a cases list")
    version = payload.get("version", 1)
    if version != SET_VERSION:
        raise SentimentSetError(f"{path}: version must be {SET_VERSION}, got {version!r}")
    cases: list[Case] = []
    seen: set[str] = set()
    for item in payload["cases"]:
        case = _case(item, path, seen)
        if split in ("all", case.split):
            cases.append(case)
    if not cases:
        raise SentimentSetError(f"{path}: no cases for split {split!r}")
    dupes = _duplicate_texts(cases)
    if dupes:
        raise SentimentSetError(f"{path}: duplicate case text: {', '.join(sorted(dupes))}")
    return tuple(cases)


def _case(item: Any, path: Path, seen: set[str]) -> Case:
    if not isinstance(item, dict):
        raise SentimentSetError(f"{path}: every case must be a mapping")
    case_id = item.get("id")
    text = item.get("text")
    if not isinstance(case_id, str) or not case_id or case_id in seen:
        raise SentimentSetError(f"{path}: id must be a unique non-empty string")
    if not isinstance(text, str) or not text.strip():
        raise SentimentSetError(f"{path}: {case_id}: text must be a non-empty string")
    try:
        sentiment = Sentiment(str(item.get("sentiment")))
    except ValueError:
        raise SentimentSetError(f"{path}: {case_id}: unknown sentiment") from None
    tags = _tags(item.get("tags", []), case_id, path)
    split = item.get("split", "dev")
    if split not in {"dev", "test"}:
        raise SentimentSetError(f"{path}: {case_id}: split must be 'dev' or 'test'")
    escalate = item.get("expect_escalation", False)
    if not isinstance(escalate, bool):
        raise SentimentSetError(f"{path}: {case_id}: expect_escalation must be a boolean")
    if escalate and sentiment is not Sentiment.NEGATIVE:
        raise SentimentSetError(
            f"{path}: {case_id}: a crisis case must be labelled negative, got {sentiment.value}"
        )
    note = item.get("note", "")
    if not isinstance(note, str):
        raise SentimentSetError(f"{path}: {case_id}: note must be a string")
    seen.add(case_id)
    return Case(
        id=case_id,
        text=text,
        sentiment=sentiment,
        tags=tags,
        split=split,
        expect_escalation=escalate,
        note=note,
    )


def _tags(raw: Any, case_id: str, path: Path) -> tuple[SignalTag, ...]:
    if not isinstance(raw, list):
        raise SentimentSetError(f"{path}: {case_id}: tags must be a list")
    tags: list[SignalTag] = []
    for item in raw:
        try:
            tag = SignalTag(str(item))
        except ValueError:
            raise SentimentSetError(f"{path}: {case_id}: unknown tag {item!r}") from None
        if tag in tags:
            raise SentimentSetError(f"{path}: {case_id}: duplicate tag {tag.value}")
        tags.append(tag)
    if len(tags) > MAX_TAGS_PER_CASE:
        raise SentimentSetError(
            f"{path}: {case_id}: at most {MAX_TAGS_PER_CASE} tags, "
            "the classifier cannot return more"
        )
    return tuple(tags)


def _duplicate_texts(cases: list[Case]) -> set[str]:
    seen: dict[str, str] = {}
    dupes: set[str] = set()
    for case in cases:
        normalized = " ".join(case.text.lower().split())
        if normalized in seen:
            dupes.add(case.id)
        seen[normalized] = case.id
    return dupes


class CountingAudit:
    """Count what the classifier did to itself, so a fallback is visible in the report."""

    def __init__(self) -> None:
        self.fallbacks = 0
        self.format_errors = 0
        self.reasons: Counter[str] = Counter()

    async def record(self, name: str, **fields: Any) -> None:
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
) -> Report:
    results: list[CaseResult] = []
    for rep in range(repeat):
        for index, case in enumerate(cases):
            if min_interval_s > 0 and index:
                await asyncio.sleep(min_interval_s)
            started = time.perf_counter()
            signal = await classifier.classify(case.text, source=case.id)
            elapsed = (time.perf_counter() - started) * 1000
            results.append(
                CaseResult(case=case, signal=signal, latency_ms=elapsed, rep=rep)
            )
    return Report(
        provider=provider,
        split=split,
        repeat=repeat,
        results=tuple(results),
        fallbacks=audit.fallbacks,
        format_errors=audit.format_errors,
        fallback_reasons=tuple(sorted(audit.reasons.items())),
    )


def render_markdown(
    report: Report,
    *,
    command: str,
    note: str,
    comparison: Comparison | None = None,
) -> str:
    cases = report.cases
    intervals = {
        "sentiment_accuracy": report.sentiment_accuracy_ci,
        "escalation_recall": report.escalation_recall_ci,
    }
    lines = [
        f"# Sentiment eval — {report.provider}",
        "",
        f"- command: `{command}`",
        f"- commit: `{_commit()}`",
        f"- environment: `{Settings().environment}`",
        f"- split: `{report.split}`",
        f"- cases: {len(cases)} ({_split_counts(cases)})",
        f"- repetitions per case: {report.repeat}",
        f"- calls: {len(report.results)}",
        "",
        "## Quality",
        "",
        "| metric | value | 95% CI |",
        "|---|---|---|",
        f"| `sentiment_accuracy` | {report.sentiment_accuracy:.3f} | "
        f"{intervals['sentiment_accuracy'].render()} |",
        f"| `case_accuracy` | {report.case_accuracy:.3f} | "
        "majority over repetitions |",
        f"| `sentiment_macro_f1` | {report.macro_f1:.3f} | — |",
        f"| `tag_precision` | {report.tag_precision:.3f} | — |",
        f"| `tag_recall` | {report.tag_recall:.3f} | — |",
        f"| `tag_f1` | {report.tag_f1:.3f} | — |",
        f"| `escalation_recall` | {report.escalation_recall:.3f} | "
        f"{intervals['escalation_recall'].render()} |",
        f"| `false_alarm_rate` | {report.false_alarm_rate:.3f} | — |",
        f"| `fallback_rate` | {report.fallback_rate:.3f} | — |",
        f"| `format_error_rate` | {report.format_error_rate:.3f} | — |",
        "",
        "## Latency",
        "",
        "| metric | value |",
        "|---|---|",
        f"| `p50_latency_ms` | {report.p50_latency_ms:.1f} |",
        f"| `p95_latency_ms` | {report.p95_latency_ms:.1f} |",
        f"| `p99_latency_ms` | {report.p99_latency_ms:.1f} |",
        "",
        "## Recall per tone",
        "",
        "| tone | recall | expected cases |",
        "|---|---|---|",
    ]
    for sentiment, recall in report.per_class_recall.items():
        expected = sum(1 for result in report.results if result.case.sentiment is sentiment)
        lines.append(f"| `{sentiment.value}` | {recall:.3f} | {expected} |")
    lines += [
        "",
        "## Confusion matrix",
        "",
        "Rows are the label, columns are the prediction.",
        "",
        "| label \\ predicted | " + " | ".join(item.value for item in Sentiment) + " |",
        "|---|" + "---|" * len(Sentiment),
    ]
    for label in Sentiment:
        row = [str(report.confusion.get((label, predicted), 0)) for predicted in Sentiment]
        lines.append(f"| `{label.value}` | " + " | ".join(row) + " |")
    lines += [
        "",
        "## Recall per tag",
        "",
        "| tag | recall | expected cases |",
        "|---|---|---|",
    ]
    for tag, recall in report.per_tag_recall.items():
        expected = sum(1 for result in report.results if tag in result.case.tags)
        lines.append(f"| `{tag.value}` | {recall:.3f} | {expected} |")
    if note:
        lines += ["", f"Note: {note}"]
    if comparison is not None:
        lines += ["", "## Comparison", "", _comparison_markdown(comparison)]
    if report.flaky_cases:
        lines += [
            "",
            "## Unstable cases",
            "",
            "A case whose verdict changed between repetitions. A gate cannot be tighter than this.",
            "",
            "| case | verdicts |",
            "|---|---|",
        ]
        for case_id in report.flaky_cases:
            seen = sorted(
                {
                    result.signal.sentiment.value
                    for result in report.results
                    if result.case.id == case_id
                }
            )
            lines.append(f"| `{case_id}` | {', '.join(seen)} |")
    if report.missed_escalations:
        lines += [
            "",
            "## Missed escalations",
            "",
            "A recruiter should have been alerted and was not. This list outranks every average.",
            "",
            "| case | expected tone | predicted tone | tags |",
            "|---|---|---|---|",
        ]
        for result in report.missed_escalations:
            tags = ", ".join(tag.value for tag in result.signal.tags)
            lines.append(
                f"| `{result.case.id}` | {result.case.sentiment.value} | "
                f"{result.signal.sentiment.value} | {tags} |"
            )
    if report.failures:
        lines += [
            "",
            "## Label failures",
            "",
            "| case | expected | got | tags |",
            "|---|---|---|---|",
        ]
        for failure in report.failures:
            tags = ", ".join(tag.value for tag in failure.signal.tags)
            lines.append(
                f"| `{failure.case.id}` | {failure.case.sentiment.value} | "
                f"{failure.signal.sentiment.value} | {tags} |"
            )
    lines.append("")
    return "\n".join(lines)


def _comparison_markdown(comparison: Comparison) -> str:
    verdict = (
        "the difference is not distinguishable from noise"
        if comparison.interval.low <= 0.0 <= comparison.interval.high
        else ("candidate is better" if comparison.delta > 0 else "candidate is worse")
    )
    return "\n".join(
        [
            f"- metric: `{comparison.metric}`",
            f"- paired cases: {comparison.paired_cases}",
            f"- baseline: {comparison.baseline:.3f}",
            f"- candidate: {comparison.candidate:.3f}",
            f"- delta: {comparison.delta:+.3f} "
            f"(95% bootstrap CI {comparison.interval.render()})",
            f"- p(delta <= 0): {comparison.p_value:.3f}",
            f"- reading: {verdict}",
        ]
    )


def _split_counts(cases: tuple[Case, ...]) -> str:
    dev = sum(1 for case in cases if case.split == "dev")
    test = len(cases) - dev
    return f"dev {dev}, test {test}"


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
    )


def render_artifact(report: Report, *, command: str) -> str:
    header = {
        "kind": "run",
        "provider": report.provider,
        "split": report.split,
        "repeat": report.repeat,
        "commit": _commit(),
        "environment": Settings().environment,
        "prompt_version": PROMPT_VERSION if report.provider == "prompt" else None,
        "rubric_version": 1 if report.provider == "jev" else None,
        "model": Settings().llm_model if report.provider == "prompt" else None,
        "command": command,
        "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "cases": len(report.cases),
        "fallbacks": report.fallbacks,
        "format_errors": report.format_errors,
        "fallback_reasons": [list(item) for item in report.fallback_reasons],
    }
    lines = [json.dumps(header, ensure_ascii=False)]
    for result in report.results:
        lines.append(
            json.dumps(
                {
                    "kind": "case",
                    "id": result.case.id,
                    "rep": result.rep,
                    "expected_sentiment": result.case.sentiment.value,
                    "predicted_sentiment": result.signal.sentiment.value,
                    "expected_tags": [tag.value for tag in result.case.tags],
                    "predicted_tags": [tag.value for tag in result.signal.tags],
                    "confidence": result.signal.confidence,
                    "expect_escalation": result.case.expect_escalation,
                    "escalated": result.level_escalates,
                    "latency_ms": round(result.latency_ms, 1),
                },
                ensure_ascii=False,
            )
        )
    return "\n".join(lines) + "\n"


def _commit() -> str:
    try:
        return subprocess.run(
            ["/usr/bin/env", "git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _classifier(
    provider: str, settings: Settings, http: httpx.AsyncClient, audit: AuditLog
) -> SentimentAnalysis:
    if provider == "prompt":
        if not settings.is_llm_configured:
            raise SentimentSetError("LLM_API_KEY is not set; the prompt provider cannot run")
        return SentimentClassifier(
            llm=build_llm(settings, SystemClock(), http),
            prompts=PromptLibrary(settings.prompts_dir),
            audit=audit,
        )
    if provider == "jev":
        if not settings.jev_api_key.get_secret_value():
            raise SentimentSetError("JEV_API_KEY is not set; the jev provider cannot run")
        return build_jev_classifier(
            client=http,
            endpoint=f"{settings.jev_base_url.rstrip('/')}/systemone",
            api_key=settings.jev_api_key,
            profile=classify_profile(settings),
            rubrics=RubricLibrary(
                settings.prompts_dir, settings.contracts_dir / "jev-rubric.schema.json"
            ),
            audit=audit,
        )

    class KeywordClassifier:
        async def classify(self, text: str, *, source: str) -> RiskSignal:
            return keyword_signal(text, source=source)

    return KeywordClassifier()


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
        f"--provider {args.provider}",
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
            classifier = _classifier(args.provider, Settings(), http, audit)
        except SentimentSetError as error:
            _abort(2, str(error))
        return await evaluate(
            cases,
            classifier,
            provider=args.provider,
            audit=audit,
            repeat=args.repeat,
            split=args.split,
            min_interval_s=args.min_interval,
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
