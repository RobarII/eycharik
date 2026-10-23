"""Golden-set evaluation.

Retrieval metrics are deterministic and run without a provider. Generation metrics need a model
and are reported separately, so a provider outage cannot be mistaken for a retrieval regression.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from onboarding.app.worker.answerer import Answerer
from onboarding.core.metrics import mean, percentile, recall_at_k, reciprocal_rank
from onboarding.core.models import EmployeeId, EmployeeProfile
from onboarding.ports import KnowledgeBase, SearchQuery

GATES = {
    "recall_at_5": 0.90,
    "mrr": 0.75,
    "citation_support": 1.0,
    "answer_contains": 1.0,
    "escalation_correctness": 0.90,
}
MAXIMUMS = {"p95_latency_ms": 8000.0}


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


@dataclass(frozen=True, slots=True)
class CaseResult:
    case: Case
    retrieved_docs: tuple[str, ...]
    recall: float
    rr: float
    retrieved_citations: int = 0
    accepted_citations: int = 0
    escalated: bool | None = None
    reason: str | None = None
    answer: str | None = None
    latency_ms: int = 0
    cost_rub: float = 0.0

    @property
    def citation_supported(self) -> bool:
        return self.retrieved_citations == self.accepted_citations

    @property
    def escalation_correct(self) -> bool:
        if self.escalated is None or self.escalated != self.case.expect_escalation:
            return False
        expected = self.case.expect_reason
        return expected is None or not self.escalated or self.reason == expected

    @property
    def contains_expected(self) -> bool:
        if not self.case.expect_contains or self.answer is None:
            return True
        lowered = self.answer.lower()
        return all(fragment.lower() in lowered for fragment in self.case.expect_contains)


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
        cases.append(
            Case(
                id=case_id,
                question=question,
                audience=str(item.get("audience", "all")),
                expect_docs=tuple(str(doc) for doc in item.get("expect_docs", ())),
                expect_contains=tuple(str(text) for text in item.get("expect_contains", ())),
                expect_escalation=bool(item.get("expect_escalation", False)),
                expect_reason=(str(item["expect_reason"]) if item.get("expect_reason") else None),
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
    cases: tuple[Case, ...],
    *,
    knowledge: KnowledgeBase,
    answerer: Answerer | None,
    on_date: date,
) -> tuple[CaseResult, ...]:
    results: list[CaseResult] = []
    for case in cases:
        profile = profile_for(case)
        retrieved = await knowledge.search(
            SearchQuery(
                text=case.question,
                audience=profile.audience,
                on_date=on_date,
                limit=5,
            )
        )
        docs = tuple(dict.fromkeys(str(chunk.chunk.doc_id) for chunk in retrieved))
        recall = recall_at_k(case.expect_docs, docs, k=5)
        rr = reciprocal_rank(case.expect_docs, docs)
        if answerer is None:
            results.append(CaseResult(case=case, retrieved_docs=docs, recall=recall, rr=rr))
            continue

        outcome = await answerer.answer(case.question, profile, on_date)
        retrieved_ids = {str(chunk.chunk.id) for chunk in outcome.retrieved}
        citations = [str(citation) for citation in outcome.citations]
        results.append(
            CaseResult(
                case=case,
                retrieved_docs=docs,
                recall=recall,
                rr=rr,
                retrieved_citations=len(citations),
                accepted_citations=sum(1 for c in citations if c in retrieved_ids),
                escalated=outcome.escalated,
                reason=outcome.reason,
                answer=outcome.text,
                latency_ms=outcome.completion.latency_ms if outcome.completion else 0,
                cost_rub=outcome.completion.cost_rub if outcome.completion else 0.0,
            )
        )
    return tuple(results)


@dataclass(frozen=True, slots=True)
class Report:
    metrics: dict[str, float]
    results: tuple[CaseResult, ...]
    generated: bool

    @property
    def failures(self) -> tuple[str, ...]:
        below = [
            name
            for name, gate in GATES.items()
            if name in self.metrics and self.metrics[name] < gate
        ]
        above = [
            name
            for name, limit in MAXIMUMS.items()
            if name in self.metrics and self.metrics[name] > limit
        ]
        return (*below, *above)


def summarise(results: tuple[CaseResult, ...], *, generated: bool) -> Report:
    # Retrieval metrics only make sense for cases that expect a document. An escalation case
    # has no expected document, and letting it score zero would punish correct refusals.
    retrieval_cases = [result for result in results if result.case.expect_docs]
    metrics: dict[str, float] = {
        "recall_at_5": mean([result.recall for result in retrieval_cases]),
        "mrr": mean([result.rr for result in retrieval_cases]),
    }
    if generated:
        latency = [float(result.latency_ms) for result in results if result.latency_ms]
        metrics["citation_support"] = mean(
            [1.0 if result.citation_supported else 0.0 for result in results]
        )
        metrics["escalation_correctness"] = mean(
            [1.0 if result.escalation_correct else 0.0 for result in results]
        )
        content_cases = [result for result in results if result.case.expect_contains]
        if content_cases:
            metrics["answer_contains"] = mean(
                [1.0 if result.contains_expected else 0.0 for result in content_cases]
            )
        if latency:
            metrics["p95_latency_ms"] = percentile(latency, p=95)
        metrics["cost_per_answer_rub"] = mean([result.cost_rub for result in results])
    return Report(metrics=metrics, results=results, generated=generated)


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
        *([f"- note: {note}"] if note else []),
        f"- cases: {len(report.results)}",
        f"- generated answers: {report.generated}",
        "",
        "| metric | value | gate |",
        "|---|---|---|",
    ]
    for name, value in report.metrics.items():
        if name in MAXIMUMS:
            limit = f"<= {MAXIMUMS[name]:.2f}"
        elif name in GATES:
            limit = f">= {GATES[name]:.2f}"
        else:
            limit = ""
        lines.append(f"| `{name}` | {value:.3f} | {limit} |")
    if report.failures:
        lines += ["", f"Failed gates: {', '.join(report.failures)}"]
    lines += [
        "",
        "## Cases",
        "",
        "| case | recall@5 | rr | escalated | reason |",
        "|---|---|---|---|---|",
    ]
    for result in report.results:
        lines.append(
            f"| `{result.case.id}` | {result.recall:.2f} | {result.rr:.2f} | "
            f"{result.escalated if result.escalated is not None else '-'} | "
            f"{result.reason or '-'} |"
        )
    return "\n".join(lines) + "\n"
