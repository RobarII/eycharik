"""Golden-set evaluation.

Retrieval metrics are deterministic and run without a provider. Generation metrics need a model
and are reported separately, so a provider outage cannot be mistaken for a retrieval regression.

Every number here is named for what it measures. ``p95_completion_ms`` is the provider call;
``p95_answer_ms`` is the whole answer including retrieval, rerank, and generation;
``cost_completion_rub`` is the completion only, because embedding and rerank cost is not reported
by the adapters yet. A reader who assumes otherwise will undercount both.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from onboarding.app.worker.answerer import Answerer
from onboarding.core.metrics import (
    mean,
    percentile,
    recall_at_k,
    reciprocal_rank,
    wilson_lower_bound,
)
from onboarding.core.models import EmployeeId, EmployeeProfile, ScoredChunk
from onboarding.evals.stats import PairedDelta, matched_pairs, paired_delta
from onboarding.ports import KnowledgeBase, KnowledgeUnavailableError, SearchQuery

# A stratum is not a label for a report; it is the unit a gate is allowed to speak about. One
# aggregate hides the stratum that broke, and the ACL stratum is the one that must never be hidden.
STRATA: tuple[str, ...] = (
    "fact",
    "neardup",
    "multihop",
    "acl",
    "escalation",
    "injection",
    "unanswerable",
    "morphology",
)
REASONS = frozenset({"no_sources", "low_confidence", "restricted", "out_of_scope", "unavailable"})

GATES: dict[str, float] = {
    "recall_at_5": 0.90,
    "mrr": 0.75,
    "context_recall_at_5": 0.90,
    "context_fragment_coverage": 0.98,
    "citation_support": 1.0,
    "answer_contains": 1.0,
    "answer_excludes": 1.0,
    "escalation_correctness": 0.90,
    # ``escalation_correctness`` is averaged over every case, so one missed crisis in 137 answers
    # costs it less than one percent. These three gate the decisions themselves, on the cases that
    # actually decide: a missed escalation, a false alarm, and a wrong routing reason.
    "escalation_recall": 0.90,
    "escalation_precision": 0.90,
    "reason_accuracy": 0.90,
}
MAXIMUMS: dict[str, float] = {
    "p95_completion_ms": 8000.0,
    "p95_answer_ms": 15000.0,
    "leak_rate": 0.0,
    "case_errors": 0.0,
}
# A stratum gate is only quoted when the stratum can carry it. Below this count the interval is
# wider than any regression worth catching.
STRATUM_MIN_CASES = 10
# Metrics a baseline may gate per stratum; latency and cost are excluded because a stratum of ten
# cases cannot make a percentile mean anything.
STRATUM_GATE_METRICS: tuple[str, ...] = (
    "recall_at_5",
    "context_recall_at_5",
    "context_fragment_coverage",
    "citation_support",
    "answer_contains",
    "answer_excludes",
    "escalation_correctness",
    "escalation_recall",
    "escalation_precision",
    "reason_accuracy",
)
COMPARE_METRICS: tuple[str, ...] = (
    "recall",
    "context_recall",
    "rr",
    "citation_supported",
    "escalation_correct",
    "escalation_matched",
    "contains_expected",
    "forbidden_clean",
)


class GoldenSetError(ValueError):
    """The golden file does not match its contract."""


@dataclass(frozen=True, slots=True)
class Case:
    id: str
    question: str
    audience: str
    expect_docs: tuple[str, ...]
    expect_contains: tuple[str, ...]
    expect_escalation: bool
    expect_reason: str | None
    # Documents that must stay invisible: other audiences, expired editions, never-indexed drafts.
    expect_absent_docs: tuple[str, ...] = ()
    # Phrases that mark a wrong answer even when the expected phrase is present: the number from
    # the expired edition next to the current one.
    expect_not_contains: tuple[str, ...] = ()
    stratum: str = "fact"


@dataclass(frozen=True, slots=True)
class CaseResult:
    case: Case
    retrieved_docs: tuple[str, ...]
    recall: float
    rr: float
    leaked_docs: tuple[str, ...] = ()
    # Documents in the context the model actually saw, after reranking. ``retrieved_docs`` is the
    # candidate list before the reranker; the difference between the two is rerank loss.
    context_docs: tuple[str, ...] = ()
    context_chunks: tuple[ScoredChunk, ...] = ()
    # A call that never returned is not a wrong answer and not a missed document: mixing it into
    # either would make an outage look like a quality regression.
    error: str = ""
    retrieved_citations: int = 0
    accepted_citations: int = 0
    escalated: bool | None = None
    reason: str | None = None
    answer: str | None = None
    completion_ms: int = 0
    answer_ms: int = 0
    cost_completion_rub: float = 0.0

    @property
    def missing_fragments_in_context(self) -> tuple[str, ...]:
        """Expected facts that were not in the prompt at all.

        ``missing_fragments`` blames the model for every absent phrase, including the ones it never
        had a chance to see. This one separates the two: a fact absent here is a retrieval or rerank
        loss, a fact present here and absent from the answer is a generation loss.
        """
        if not self.context_docs:
            return self.case.expect_contains
        context = " ".join(chunk.chunk.text for chunk in self.context_chunks).lower()
        return tuple(
            fragment for fragment in self.case.expect_contains if fragment.lower() not in context
        )

    @property
    def context_recall(self) -> float:
        if not self.context_docs:
            return 0.0
        return recall_at_k(self.case.expect_docs, self.context_docs, k=len(self.context_docs))

    @property
    def leaked(self) -> bool:
        """True when a document the viewer must not see reached the retrieval result."""
        return bool(self.leaked_docs)

    @property
    def citation_supported(self) -> bool:
        """Every citation came from the retrieved context, and an answer cites something.

        An empty citation list used to pass, because zero citations are all "supported". An
        non-escalated answer that cites nothing is exactly the case a reader needs to see.
        """
        if not self.escalated and self.retrieved_citations == 0:
            return False
        return self.retrieved_citations == self.accepted_citations

    @property
    def escalation_correct(self) -> bool:
        if self.escalated is None or self.escalated != self.case.expect_escalation:
            return False
        expected = self.case.expect_reason
        return expected is None or not self.escalated or self.reason == expected

    @property
    def missing_fragments(self) -> tuple[str, ...]:
        """The expected fragments the answer did not contain. Empty means the case passed."""
        if not self.case.expect_contains or self.answer is None:
            return ()
        lowered = self.answer.lower()
        return tuple(
            fragment for fragment in self.case.expect_contains if fragment.lower() not in lowered
        )

    @property
    def forbidden_fragments(self) -> tuple[str, ...]:
        """Phrases from another edition that reached the answer: the wrong number, stated."""
        if not self.case.expect_not_contains or self.answer is None:
            return ()
        lowered = self.answer.lower()
        return tuple(
            fragment for fragment in self.case.expect_not_contains if fragment.lower() in lowered
        )

    @property
    def contains_expected(self) -> bool:
        return not self.missing_fragments

    @property
    def forbidden_clean(self) -> bool:
        return not self.forbidden_fragments


def load_cases(path: Path) -> tuple[Case, ...]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("cases"), list):
        raise GoldenSetError(f"{path}: expected a mapping with a 'cases' list")
    cases: list[Case] = []
    seen: set[str] = set()
    for index, item in enumerate(raw["cases"]):
        if not isinstance(item, dict):
            raise GoldenSetError(f"{path}: case {index} is not a mapping")
        case_id = str(item.get("id", ""))
        question = str(item.get("question", ""))
        if not case_id or not question:
            raise GoldenSetError(f"{path}: case {index} needs id and question")
        if case_id in seen:
            raise GoldenSetError(f"{path}: duplicate case id {case_id!r}")
        seen.add(case_id)
        stratum = str(item.get("stratum", ""))
        if stratum not in STRATA:
            raise GoldenSetError(f"{path}: case {case_id!r} needs a known stratum, got {stratum!r}")
        expect_docs = tuple(str(doc) for doc in item.get("expect_docs", ()))
        absent_docs = tuple(str(doc) for doc in item.get("expect_absent_docs", ()))
        contains = tuple(str(text) for text in item.get("expect_contains", ()))
        not_contains = tuple(str(text) for text in item.get("expect_not_contains", ()))
        if set(expect_docs) & set(absent_docs):
            raise GoldenSetError(f"{path}: case {case_id!r} expects and forbids the same document")
        if set(contains) & set(not_contains):
            raise GoldenSetError(f"{path}: case {case_id!r} contains and forbids the same phrase")
        if stratum == "neardup" and not not_contains:
            raise GoldenSetError(
                f"{path}: neardup case {case_id!r} needs expect_not_contains: a competing number"
            )
        if stratum == "acl" and not absent_docs:
            raise GoldenSetError(
                f"{path}: acl case {case_id!r} needs expect_absent_docs: a document to hide"
            )
        expect_reason = str(item["expect_reason"]) if item.get("expect_reason") else None
        if expect_reason is not None and expect_reason not in REASONS:
            raise GoldenSetError(f"{path}: case {case_id!r} has unknown reason {expect_reason!r}")
        cases.append(
            Case(
                id=case_id,
                question=question,
                audience=str(item.get("audience", "all")),
                expect_docs=expect_docs,
                expect_absent_docs=absent_docs,
                expect_contains=contains,
                expect_not_contains=not_contains,
                expect_escalation=bool(item.get("expect_escalation", False)),
                expect_reason=expect_reason,
                stratum=stratum,
            )
        )
    if not cases:
        raise GoldenSetError(f"{path}: no cases")
    return tuple(cases)


def profile_for(case: Case, *, employee_id: str = "eval") -> EmployeeProfile:
    audience = ("all",) if case.audience == "all" else ("all", case.audience)
    return EmployeeProfile(
        employee_id=EmployeeId(employee_id),
        name="Сотрудник",
        role="Специалист",
        department="Компания",
        started_at=date(2026, 10, 1),
        audience=audience,
    )


async def evaluate(
    cases: Sequence[Case],
    *,
    knowledge: KnowledgeBase,
    answerer: Answerer | None,
    on_date: date,
) -> tuple[CaseResult, ...]:
    results: list[CaseResult] = []
    for case in cases:
        profile = profile_for(case)
        try:
            retrieved = await knowledge.search(
                SearchQuery(
                    text=case.question,
                    audience=profile.audience,
                    on_date=on_date,
                    limit=5,
                )
            )
        except KnowledgeUnavailableError as error:
            results.append(
                CaseResult(
                    case=case, retrieved_docs=(), recall=0.0, rr=0.0, error=f"retrieval: {error}"
                )
            )
            continue
        docs = tuple(dict.fromkeys(str(chunk.chunk.doc_id) for chunk in retrieved))
        recall = recall_at_k(case.expect_docs, docs, k=5)
        rr = reciprocal_rank(case.expect_docs, docs)
        leaked = tuple(doc for doc in docs if doc in case.expect_absent_docs)
        if answerer is None:
            results.append(
                CaseResult(
                    case=case,
                    retrieved_docs=docs,
                    recall=recall,
                    rr=rr,
                    leaked_docs=leaked,
                )
            )
            continue

        started = time.perf_counter()
        try:
            outcome = await answerer.answer(case.question, profile, on_date)
        except KnowledgeUnavailableError as error:
            results.append(
                CaseResult(
                    case=case,
                    retrieved_docs=docs,
                    recall=recall,
                    rr=rr,
                    leaked_docs=leaked,
                    error=f"answer: {error}",
                )
            )
            continue
        answer_ms = int((time.perf_counter() - started) * 1000)
        context_docs = tuple(dict.fromkeys(str(chunk.chunk.doc_id) for chunk in outcome.retrieved))
        retrieved_ids = {str(chunk.chunk.id) for chunk in outcome.retrieved}
        citations = [str(citation) for citation in outcome.citations]
        results.append(
            CaseResult(
                case=case,
                retrieved_docs=docs,
                recall=recall,
                rr=rr,
                leaked_docs=leaked,
                context_docs=context_docs,
                context_chunks=outcome.retrieved,
                retrieved_citations=len(citations),
                accepted_citations=sum(1 for c in citations if c in retrieved_ids),
                escalated=outcome.escalated,
                reason=outcome.reason,
                answer=outcome.text,
                completion_ms=outcome.completion.latency_ms if outcome.completion else 0,
                answer_ms=answer_ms,
                cost_completion_rub=outcome.completion.cost_rub if outcome.completion else 0.0,
            )
        )
    return tuple(results)


@dataclass(frozen=True, slots=True)
class Baseline:
    """Gates pinned to a known-good run.

    ``overall`` and ``strata`` hold the minimum a metric may take. They are derived from the
    Wilson lower bound of the baseline observation, not from taste, so a run that loses quality
    inside provider noise still passes and a run that loses more does not.
    """

    commit: str = ""
    overall: dict[str, float] = field(default_factory=dict)
    strata: dict[str, dict[str, float]] = field(default_factory=dict)

    def gates_for(self, stratum: str) -> dict[str, float]:
        return self.strata.get(stratum, {})


def load_baseline(path: Path) -> Baseline | None:
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise GoldenSetError(f"{path}: expected a JSON object")
    overall = raw.get("overall") or {}
    strata = raw.get("strata") or {}
    if not isinstance(overall, dict) or not isinstance(strata, dict):
        raise GoldenSetError(f"{path}: 'overall' and 'strata' must be objects")
    return Baseline(
        commit=str(raw.get("commit", "")),
        overall={str(k): float(v) for k, v in overall.items()},
        strata={
            str(name): {str(k): float(v) for k, v in gates.items()}
            for name, gates in strata.items()
            if isinstance(gates, dict)
        },
    )


def derive_baseline(report: Report, *, commit: str) -> Baseline:
    """Pin the current run as the baseline: gate = Wilson lower bound, floored to 0.01."""
    overall: dict[str, float] = {}
    for name, value in report.metrics.items():
        if name in MAXIMUMS:
            overall[name] = MAXIMUMS[name]
            continue
        if name not in GATES:
            continue
        n = _sample_size(report, name)
        overall[name] = _floor(wilson_lower_bound(value, n))
    strata: dict[str, dict[str, float]] = {}
    for stratum, metrics in report.strata.items():
        if report.counts.get(stratum, 0) < STRATUM_MIN_CASES:
            continue
        gates = {
            name: _floor(wilson_lower_bound(value, report.counts[stratum]))
            for name, value in metrics.items()
            if name in STRATUM_GATE_METRICS
        }
        if gates:
            strata[stratum] = gates
    return Baseline(commit=commit, overall=overall, strata=strata)


def _any_result(result: CaseResult) -> bool:
    return True


def _expects_absent_docs(result: CaseResult) -> bool:
    return bool(result.case.expect_absent_docs)


def _expects_docs(result: CaseResult) -> bool:
    return bool(result.case.expect_docs)


def _expects_escalation(result: CaseResult) -> bool:
    return result.case.expect_escalation


def _escalated(result: CaseResult) -> bool:
    return bool(result.escalated)


def _expects_reason(result: CaseResult) -> bool:
    return result.case.expect_reason is not None


def _bans_phrases(result: CaseResult) -> bool:
    return bool(result.case.expect_not_contains)


def _expects_phrases(result: CaseResult) -> bool:
    return bool(result.case.expect_contains) and result.answer is not None


# Which cases belong in a metric's denominator. A case that expects no document cannot miss one,
# and a call that never returned is an outage rather than a quality signal, so neither counts.
SAMPLE_DENOMINATORS: dict[str, Callable[[CaseResult], bool]] = {
    "leak_rate": _expects_absent_docs,
    "recall_at_5": _expects_docs,
    "mrr": _expects_docs,
    "escalation_recall": _expects_escalation,
    "escalation_precision": _escalated,
    "reason_accuracy": _expects_reason,
    "answer_excludes": _bans_phrases,
    "answer_contains": _expects_phrases,
}


def baseline_refusal(report: Report) -> str | None:
    """Why this run may not become the baseline, or ``None`` when it may.

    A baseline is derived from a run that passed. Pinning a failing run lowers every gate to what
    the failure already achieved — the next run then cannot fail, which is the opposite of the
    reason the file exists.
    """
    if not report.failures:
        return None
    return (
        "this run failed "
        + ", ".join(report.failures)
        + "; fix it or pass --force-baseline, because a pinned failure lowers the gates"
    )


def _sample_size(report: Report, metric: str) -> int:
    predicate = SAMPLE_DENOMINATORS.get(metric, _any_result)
    return max(1, sum(1 for result in report.results if not result.error and predicate(result)))


def _floor(value: float) -> float:
    return int(value * 100.0) / 100.0


def baseline_json(baseline: Baseline) -> str:
    payload = {
        "commit": baseline.commit,
        "overall": dict(sorted(baseline.overall.items())),
        "strata": {
            name: dict(sorted(gates.items())) for name, gates in sorted(baseline.strata.items())
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


@dataclass(frozen=True, slots=True)
class Report:
    metrics: dict[str, float]
    results: tuple[CaseResult, ...]
    generated: bool
    strata: dict[str, dict[str, float]] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)
    baseline: Baseline | None = None

    @property
    def gates(self) -> dict[str, float]:
        """Overall gates: the code default, overridden by a pinned baseline."""
        if self.baseline is None or not self.baseline.overall:
            return dict(GATES)
        return {**GATES, **self.baseline.overall}

    @property
    def failures(self) -> tuple[str, ...]:
        gates = self.gates
        below = [
            name
            for name, gate in gates.items()
            if name in self.metrics and self.metrics[name] < gate
        ]
        above = [
            name
            for name, limit in MAXIMUMS.items()
            if name in self.metrics and self.metrics[name] > limit
        ]
        per_stratum: list[str] = []
        if self.baseline is not None:
            for stratum, gates_for_stratum in self.baseline.strata.items():
                if self.counts.get(stratum, 0) < STRATUM_MIN_CASES:
                    continue
                metrics = self.strata.get(stratum, {})
                per_stratum.extend(
                    f"{stratum}.{name}"
                    for name, gate in gates_for_stratum.items()
                    if name in metrics and metrics[name] < gate
                )
        return (*below, *above, *per_stratum)


def _metrics(results: Sequence[CaseResult], *, generated: bool) -> dict[str, float]:
    failed = [result for result in results if result.error]
    retrieval_cases = [result for result in results if result.case.expect_docs and not result.error]
    metrics: dict[str, float] = {
        "recall_at_5": mean([result.recall for result in retrieval_cases]),
        "mrr": mean([result.rr for result in retrieval_cases]),
    }
    if failed:
        metrics["case_errors"] = float(len(failed))
    answered = [result for result in results if not result.error]
    # A case with a forbidden document checks confidentiality or validity, not recall: a leak
    # makes the answer wrong even when the expected document was also retrieved.
    guarded = [result for result in answered if result.case.expect_absent_docs]
    if guarded:
        metrics["leak_rate"] = mean([1.0 if result.leaked else 0.0 for result in guarded])
    if not generated:
        return metrics

    # What the reranker kept out of the candidates the model was handed. Without this the report
    # can show perfect retrieval while the answer fails because the reranker dropped the one
    # document that held the fact.
    context_cases = [
        result for result in answered if result.case.expect_docs and result.context_docs
    ]
    if context_cases:
        metrics["context_recall_at_5"] = mean([result.context_recall for result in context_cases])
    fact_cases = [
        result for result in context_cases if result.case.expect_contains and result.context_chunks
    ]
    if fact_cases:
        metrics["context_fragment_coverage"] = mean(
            [1.0 if not result.missing_fragments_in_context else 0.0 for result in fact_cases]
        )
    completion = [float(result.completion_ms) for result in answered if result.completion_ms]
    if completion:
        metrics["p95_completion_ms"] = percentile(completion, p=95)
    whole = [float(result.answer_ms) for result in answered if result.answer_ms]
    if whole:
        metrics["p95_answer_ms"] = percentile(whole, p=95)
    metrics["citation_support"] = mean(
        [1.0 if result.citation_supported else 0.0 for result in answered]
    )
    metrics["escalation_correctness"] = mean(
        [1.0 if result.escalation_correct else 0.0 for result in answered]
    )
    # The denominators are the cases that decide, not the whole set: a missed crisis is only
    # visible when the metric asks "of the cases that had to escalate, how many did".
    expected_escalations = [result for result in answered if result.case.expect_escalation]
    if expected_escalations:
        metrics["escalation_recall"] = mean(
            [1.0 if result.escalated else 0.0 for result in expected_escalations]
        )
    escalations = [result for result in answered if result.escalated]
    if escalations:
        metrics["escalation_precision"] = mean(
            [1.0 if result.case.expect_escalation else 0.0 for result in escalations]
        )
    reasoned = [
        result
        for result in answered
        if result.case.expect_escalation and result.case.expect_reason is not None
    ]
    if reasoned:
        metrics["reason_accuracy"] = mean(
            [1.0 if result.reason == result.case.expect_reason else 0.0 for result in reasoned]
        )
    content_cases = [result for result in answered if result.case.expect_contains]
    if content_cases:
        metrics["answer_contains"] = mean(
            [1.0 if result.contains_expected else 0.0 for result in content_cases]
        )
    forbidden_cases = [result for result in answered if result.case.expect_not_contains]
    if forbidden_cases:
        metrics["answer_excludes"] = mean(
            [1.0 if result.forbidden_clean else 0.0 for result in forbidden_cases]
        )
    metrics["cost_completion_rub"] = mean([result.cost_completion_rub for result in answered])
    return metrics


def summarise(
    results: tuple[CaseResult, ...],
    *,
    generated: bool,
    baseline: Baseline | None = None,
) -> Report:
    strata: dict[str, dict[str, float]] = {}
    counts: dict[str, int] = {}
    for stratum in STRATA:
        subset = tuple(result for result in results if result.case.stratum == stratum)
        if not subset:
            continue
        counts[stratum] = len(subset)
        strata[stratum] = _metrics(subset, generated=generated)
    return Report(
        metrics=_metrics(results, generated=generated),
        results=results,
        generated=generated,
        strata=strata,
        counts=counts,
        baseline=baseline,
    )


def case_record(result: CaseResult) -> dict[str, Any]:
    """One JSONL line per case. The artifact is what makes two runs comparable."""
    return {
        "case": result.case.id,
        "stratum": result.case.stratum,
        "audience": result.case.audience,
        "error": result.error,
        "retrieved": list(result.retrieved_docs),
        "context": list(result.context_docs),
        "leaked": list(result.leaked_docs),
        "missing": list(result.missing_fragments),
        "forbidden": list(result.forbidden_fragments),
        "recall": result.recall,
        "context_recall": result.context_recall,
        "rr": result.rr,
        "citation_supported": 1.0 if result.citation_supported else 0.0,
        "escalation_correct": 1.0 if result.escalation_correct else 0.0,
        "escalation_matched": 1.0
        if result.escalated is not None and result.escalated == result.case.expect_escalation
        else 0.0,
        "contains_expected": 1.0 if result.contains_expected else 0.0,
        "forbidden_clean": 1.0 if result.forbidden_clean else 0.0,
        "escalated": result.escalated,
        "reason": result.reason,
        "completion_ms": result.completion_ms,
        "answer_ms": result.answer_ms,
        "cost_completion_rub": result.cost_completion_rub,
    }


def write_jsonl(report: Report, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(case_record(result), ensure_ascii=False) for result in report.results]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict) or "case" not in raw:
            raise GoldenSetError(f"{path}: every line needs a 'case' field")
        records[str(raw["case"])] = raw
    return records


def compare_records(
    current: Mapping[str, Mapping[str, Any]],
    baseline: Mapping[str, Mapping[str, Any]],
    *,
    seed: int | None = None,
) -> tuple[PairedDelta, ...]:
    """Paired comparison over the cases both runs scored, one :class:`PairedDelta` per metric."""
    deltas: list[PairedDelta] = []
    for metric in COMPARE_METRICS:
        current_metric = {case: float(record.get(metric, 0.0)) for case, record in current.items()}
        baseline_metric = {
            case: float(record.get(metric, 0.0)) for case, record in baseline.items()
        }
        pairs = matched_pairs(current_metric, baseline_metric)
        if seed is None:
            deltas.append(paired_delta(metric, pairs))
        else:
            deltas.append(paired_delta(metric, pairs, seed=seed))
    return tuple(deltas)


def render_comparison(deltas: Sequence[PairedDelta]) -> str:
    lines = [
        "| metric | current | baseline | delta | 95% CI | p(delta <= 0) | n |",
        "|---|---|---|---|---|---|---|",
    ]
    for delta in deltas:
        verdict = "regression" if delta.regression else "-"
        lines.append(
            f"| `{delta.metric}` | {delta.current:.3f} | {delta.baseline:.3f} | "
            f"{delta.delta:+.3f} | [{delta.low:+.3f}, {delta.high:+.3f}] | "
            f"{delta.p_le_zero:.3f} | {delta.n} ({verdict}) |"
        )
    return "\n".join(lines)


def render_markdown(
    report: Report,
    *,
    command: str,
    commit: str,
    model: str,
    environment: str,
    embed_provider: str,
    note: str | None,
    on_date: date,
    retrieval: str = "",
    artifact: str = "",
    comparison: Sequence[PairedDelta] = (),
) -> str:
    status = "FAIL" if report.failures else "PASS"
    lines = [
        f"# Eval {on_date.isoformat()} — {status}",
        "",
        f"- command: `{command}`",
        f"- commit: `{commit}`",
        f"- model: `{model}`",
        f"- environment: `{environment}`",
        f"- embed provider: `{embed_provider}`",
        *([f"- retrieval: `{retrieval}`"] if retrieval else []),
        *([f"- artifact: `{artifact}`"] if artifact else []),
        *([f"- baseline: `{report.baseline.commit}`"] if report.baseline else []),
        *([f"- note: {note}"] if note else []),
        f"- cases: {len(report.results)}",
        f"- generated answers: {report.generated}",
        "",
        "| metric | value | gate |",
        "|---|---|---|",
    ]
    lines += _render_metrics(report)
    if report.failures:
        lines += ["", f"Failed gates: {', '.join(report.failures)}"]
    lines += _render_strata(report)
    lines += _render_comparison(comparison)
    lines += _render_cases(report)
    return "\n".join(lines) + "\n"


def _render_metrics(report: Report) -> list[str]:
    gates = report.gates
    lines: list[str] = []
    for name, value in report.metrics.items():
        if name == "case_errors":
            lines.append(f"| `{name}` | {value:.0f} | <= {MAXIMUMS[name]:.0f} |")
            continue
        if name in MAXIMUMS:
            limit = f"<= {MAXIMUMS[name]:.2f}"
        elif name in gates:
            limit = f">= {gates[name]:.2f}"
        else:
            limit = ""
        lines.append(f"| `{name}` | {value:.3f} | {limit} |")
    return lines


def _render_strata(report: Report) -> list[str]:
    if not report.strata:
        return []
    lines = [
        "",
        "## Strata",
        "",
        "One aggregate hides the stratum that broke. A gate is quoted per stratum only",
        f"when the stratum holds at least {STRATUM_MIN_CASES} cases.",
        "",
        "| stratum | cases | recall@5 | context@5 | mrr | escalation | contains |",
        "|---|---|---|---|---|---|---|",
    ]
    for stratum, metrics in report.strata.items():
        lines.append(
            f"| `{stratum}` | {report.counts[stratum]} | "
            f"{_value(metrics, 'recall_at_5')} | {_value(metrics, 'context_recall_at_5')} | "
            f"{_value(metrics, 'mrr')} | {_value(metrics, 'escalation_correctness')} | "
            f"{_value(metrics, 'answer_contains')} |"
        )
    return lines


def _render_comparison(comparison: Sequence[PairedDelta]) -> list[str]:
    if not comparison:
        return []
    return [
        "",
        "## Comparison against baseline",
        "",
        "Paired bootstrap over the cases both runs scored: two standalone numbers are not a",
        "comparison, the same cases resampled together are.",
        "",
        render_comparison(comparison),
    ]


def _render_cases(report: Report) -> list[str]:
    lines = [
        "",
        "## Cases",
        "",
        "| case | stratum | recall@5 | ctx@5 | rr | leaked | escalated | reason "
        "| missing | forbidden |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for result in report.results:
        lines.append(_render_case_row(result))
    failures = [
        result
        for result in report.results
        if result.missing_fragments or result.forbidden_fragments or not result.escalation_correct
    ]
    if not failures:
        return lines
    lines += [
        "",
        "## Failures in detail",
        "",
        "A failing gate needs the answer that failed it, not just the count: the same number",
        "can mean a wrong fact, a wrong format, or a confidently answered question that should",
        "have escalated.",
        "",
    ]
    for result in failures:
        lines += _render_failure(result)
    return lines


def _render_case_row(result: CaseResult) -> str:
    if result.error:
        return (
            f"| `{result.case.id}` | `{result.case.stratum}` | - | - | - | - | error | "
            f"`{result.error}` | - | - |"
        )
    leaked = ",".join(result.leaked_docs) if result.leaked_docs else "-"
    missing = ", ".join(result.missing_fragments) or "-"
    forbidden = ", ".join(result.forbidden_fragments) or "-"
    escalated = result.escalated if result.escalated is not None else "-"
    context = result.context_recall if result.context_docs else "-"
    return (
        f"| `{result.case.id}` | `{result.case.stratum}` | {result.recall:.2f} | "
        f"{context} | {result.rr:.2f} | {leaked} | {escalated} | "
        f"{result.reason or '-'} | {missing} | {forbidden} |"
    )


def _render_failure(result: CaseResult) -> list[str]:
    expected_reason = result.case.expect_reason or "-"
    return [
        f"### `{result.case.id}` — {result.case.question}",
        "",
        f"- stratum: `{result.case.stratum}`",
        f"- audience: `{result.case.audience}`",
        f"- escalated: {result.escalated} (expected {result.case.expect_escalation})",
        f"- escalation reason: {result.reason or '-'} (expected {expected_reason})",
        f"- missing fragments: {', '.join(result.missing_fragments) or '-'}",
        f"- forbidden fragments: {', '.join(result.forbidden_fragments) or '-'}",
        f"- retrieved: {', '.join(result.retrieved_docs) or '-'}",
        f"- context: {', '.join(result.context_docs) or '-'}",
        "",
        "```",
        (result.answer or "<no answer>").strip()[:800],
        "```",
        "",
    ]


def _value(metrics: Mapping[str, float], name: str) -> str:
    return f"{metrics[name]:.2f}" if name in metrics else "-"
