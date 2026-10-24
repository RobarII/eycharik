"""What a sentiment run measured: the report, its intervals, and the paired comparison.

A report is a value, not a service: it holds the results and computes every number the gate reads.
Keeping it apart from the run means a metric can be tested by building a report from a handful of
results, with no provider, no key and no sleep. The intervals are Wilson, the comparison is a paired
bootstrap, and both are deterministic given the seed — a gate that moves on its own cannot fail.

``load_artifact`` is here for the same reason: reading an earlier run back into a report has to
produce the same value the writer started from.
"""

from __future__ import annotations

import json
import math
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from onboarding.core.models import RiskLevel, RiskSignal, Sentiment, SignalTag
from onboarding.core.risk import assess
from onboarding.evals.sentiment_cases import Case, SentimentSetError

Z_95 = 1.959963984540054
BOOTSTRAP_ROUNDS = 5000
BOOTSTRAP_SEED = 20261023


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
