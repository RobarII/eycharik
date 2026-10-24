"""Rerank delta: one stage measured on its own.

``--retrieval-only`` calls the knowledge base directly, so the reranker never runs there, and a full
run mixes the ranking with generation, latency, and cost. This scope closes that gap: search, then
rerank, then recall@5 and MRR before and after, plus the per-call latency the stage budget has to
hold.

No gates and no baseline. The reranker is an improvement, not a dependency (ADR 0008): a stage that
fails still answers, so there is no threshold to fail. What the number decides is whether the
cross-encoder earns its latency on this corpus, and that is a reading, not a pass.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import httpx

from onboarding.app.clock import SystemClock
from onboarding.app.container import build_container
from onboarding.app.llm.profiles import rerank_profile
from onboarding.app.llm.rerank import build_reranker
from onboarding.app.settings import Settings
from onboarding.core.metrics import percentile, recall_at_k, reciprocal_rank
from onboarding.core.models import ScoredChunk
from onboarding.evals.__main__ import retrieval_label
from onboarding.evals.artifact import commit_hash, stem, write_pair
from onboarding.evals.runner import Case, load_cases, profile_for
from onboarding.ports import KnowledgeBase, Reranker, SearchQuery

ROOT = Path(__file__).resolve().parents[4]
GOLDEN = ROOT / "docs" / "evals" / "golden.yaml"


@dataclass(frozen=True, slots=True)
class CaseDelta:
    """One question, before and after the cross-encoder.

    ``before_docs`` is the candidate list the fusion produced, truncated to the same window the
    reranker returns, so the two orders are compared at one length and a longer list cannot win by
    accident.
    """

    case_id: str
    before_docs: tuple[str, ...]
    after_docs: tuple[str, ...]
    before_recall: float
    before_rr: float
    after_recall: float
    after_rr: float
    latency_ms: float = 0.0
    error: str = ""

    @property
    def reordered(self) -> bool:
        return self.after_docs != self.before_docs[: len(self.after_docs)]


@dataclass(frozen=True, slots=True)
class Delta:
    """The aggregate a reader compares against the retrieval-only run on the same set."""

    cases: int
    failures: int
    reordered: int
    before_recall: float
    after_recall: float
    before_mrr: float
    after_mrr: float
    latency_p50_ms: float
    latency_p95_ms: float


def deltas(records: Sequence[CaseDelta]) -> Delta:
    """Means over the cases that answered, counted, never guessed.

    A failed call is dropped from quality and counted separately: a reranker outage keeps the fused
    order, so folding it in would report the pre-rerank number as if the model had disagreed.
    """
    answered = [record for record in records if not record.error]
    latencies = [record.latency_ms for record in answered]
    return Delta(
        cases=len(records),
        failures=len(records) - len(answered),
        reordered=sum(1 for record in answered if record.reordered),
        before_recall=_mean(record.before_recall for record in answered),
        after_recall=_mean(record.after_recall for record in answered),
        before_mrr=_mean(record.before_rr for record in answered),
        after_mrr=_mean(record.after_rr for record in answered),
        latency_p50_ms=percentile(latencies, p=50),
        latency_p95_ms=percentile(latencies, p=95),
    )


def _mean(values: Iterable[float]) -> float:
    materialised = list(values)
    return statistics.fmean(materialised) if materialised else 0.0


async def measure(
    cases: Sequence[Case],
    *,
    knowledge: KnowledgeBase,
    reranker: Reranker,
    recall_limit: int,
    rerank_limit: int,
    on_date: date,
    clock: Callable[[], float] = time.perf_counter,
) -> tuple[CaseDelta, ...]:
    """Search, rerank, and score both orders. Cases that expect no document carry no rank."""
    records: list[CaseDelta] = []
    for case in cases:
        profile = profile_for(case)
        candidates = await knowledge.search(
            SearchQuery(
                text=case.question,
                audience=profile.audience,
                on_date=on_date,
                limit=recall_limit,
            )
        )
        fused = tuple(dict.fromkeys(str(chunk.chunk.doc_id) for chunk in candidates))
        window = min(rerank_limit, len(fused))
        before = fused[:window]
        before_recall = recall_at_k(case.expect_docs, before, k=len(before) or 1)
        before_rr = reciprocal_rank(case.expect_docs, before)
        if len(candidates) < 2:
            records.append(
                CaseDelta(
                    case_id=case.id,
                    before_docs=before,
                    after_docs=before,
                    before_recall=before_recall,
                    before_rr=before_rr,
                    after_recall=before_recall,
                    after_rr=before_rr,
                )
            )
            continue
        started = clock()
        try:
            order = await reranker.rerank(
                case.question,
                tuple(chunk.chunk.text for chunk in candidates),
                top_n=rerank_limit,
            )
        except Exception as error:  # noqa: BLE001 - the stage degrades, and the run records it
            records.append(
                CaseDelta(
                    case_id=case.id,
                    before_docs=before,
                    after_docs=before,
                    before_recall=before_recall,
                    before_rr=before_rr,
                    after_recall=before_recall,
                    after_rr=before_rr,
                    error=f"{type(error).__name__}: {error}",
                )
            )
            continue
        elapsed_ms = (clock() - started) * 1000.0
        after = _reranked_docs(candidates, order, rerank_limit)
        records.append(
            CaseDelta(
                case_id=case.id,
                before_docs=before,
                after_docs=after,
                before_recall=before_recall,
                before_rr=before_rr,
                after_recall=recall_at_k(case.expect_docs, after, k=len(after) or 1),
                after_rr=reciprocal_rank(case.expect_docs, after),
                latency_ms=elapsed_ms,
            )
        )
    return tuple(records)


def _reranked_docs(
    candidates: Sequence[ScoredChunk], order: Sequence[int], rerank_limit: int
) -> tuple[str, ...]:
    """Document ids in the reranked order, deduplicated like the fused list they came from."""
    kept = [
        str(candidates[index].chunk.doc_id)
        for index in order[:rerank_limit]
        if 0 <= index < len(candidates)
    ]
    return tuple(dict.fromkeys(kept))


def render(
    delta: Delta,
    *,
    command: str,
    commit: str,
    environment: str,
    retrieval: str,
    artifact: str,
    note: str | None,
    on_date: date,
) -> str:
    lines = [
        f"# Оценка {on_date.isoformat()}: дельта переранжирования",
        "",
        f"- команда: `{command}`",
        f"- коммит: `{commit}`",
        "- модель: `n/a`",
        f"- окружение: `{environment}`",
        f"- поиск: `{retrieval}`",
        f"- артефакт: `{artifact}`",
        *([f"- заметка: {note}"] if note else []),
        f"- кейсов: {delta.cases}",
        "- сгенерированные ответы: False",
        "",
        "Считаются только кейсы с ожидаемым документом: там, где ожидать нечего, ранга нет.",
        "",
        "| метрика | до реранка | после |",
        "|---|---|---|",
        f"| `recall@5` | {_metric(delta.before_recall)} | {_metric(delta.after_recall)} |",
        f"| `mrr` | {_metric(delta.before_mrr)} | {_metric(delta.after_mrr)} |",
        "",
        "| счёт | значение |",
        "|---|---|",
        f"| порядок изменился | {delta.reordered} / {delta.cases - delta.failures} |",
        f"| отказов | {delta.failures} |",
        f"| латентность реранка, `p50` | {delta.latency_p50_ms:.0f} мс |",
        f"| латентность реранка, `p95` | {delta.latency_p95_ms:.0f} мс |",
        "",
        "Гейта нет: реранкер — улучшение, а не зависимость (ADR 0008). Отказ оставляет",
        "гибридный порядок, поэтому `mrr` до реранка и есть запасной вариант.",
    ]
    return "\n".join(lines) + "\n"


def _metric(value: float) -> str:
    return f"{value:.3f}"


def _jsonl(records: Sequence[CaseDelta]) -> str:
    lines = []
    for record in records:
        lines.append(
            json.dumps(
                {
                    "case": record.case_id,
                    "before": list(record.before_docs),
                    "after": list(record.after_docs),
                    "reordered": record.reordered,
                    "before_recall": round(record.before_recall, 6),
                    "after_recall": round(record.after_recall, 6),
                    "before_rr": round(record.before_rr, 6),
                    "after_rr": round(record.after_rr, 6),
                    "latency_ms": round(record.latency_ms, 3),
                    "error": record.error,
                },
                ensure_ascii=False,
            )
        )
    return "\n".join(lines) + ("\n" if lines else "")


async def _run(settings: Settings, cases: Sequence[Case], on_date: date) -> tuple[CaseDelta, ...]:
    """One event loop for the container, the reranker, and the shutdown: they share a client."""
    client = httpx.AsyncClient(trust_env=False)
    container = build_container(settings)
    reranker = build_reranker(settings, client, clock=SystemClock())
    assert reranker is not None  # main() refuses to get here without one
    try:
        return await measure(
            cases,
            knowledge=container.knowledge,
            reranker=reranker,
            recall_limit=settings.recall_limit,
            rerank_limit=settings.rerank_limit,
            on_date=on_date,
        )
    finally:
        await container.aclose()
        await client.aclose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="onboarding.evals.rerank")
    parser.add_argument("--golden", type=Path, default=GOLDEN)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "docs" / "measurements")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--label", default="")
    parser.add_argument("--note", default="")
    parser.add_argument("--limit", type=int, default=0, help="run only the first N cases")
    args = parser.parse_args(argv)

    settings = Settings()
    cases = tuple(case for case in load_cases(args.golden) if case.expect_docs)
    if args.limit:
        cases = cases[: args.limit]
    if not cases:
        print("no case expects a document; the delta would be undefined", file=sys.stderr)
        return 2
    if rerank_profile(settings) is None:
        print(
            "RERANK_BASE_URL is empty: there is no reranker to measure. "
            "Point it at a profile with a Cohere-shaped /rerank.",
            file=sys.stderr,
        )
        return 2

    on_date = datetime.now(UTC).date()
    records = asyncio.run(_run(settings, cases, on_date))
    delta = deltas(records)

    print(f"{'measure':<10}{'before':>10}{'after':>10}")
    print("-" * 30)
    print(f"{'recall@5':<10}{delta.before_recall:>10.3f}{delta.after_recall:>10.3f}")
    print(f"{'mrr':<10}{delta.before_mrr:>10.3f}{delta.after_mrr:>10.3f}")
    print()
    print(f"cases            {delta.cases}")
    print(f"rerank failures  {delta.failures}")
    print(f"order changed on {delta.reordered} / {delta.cases - delta.failures}")
    print(f"rerank latency   p50 {delta.latency_p50_ms:.0f} ms  p95 {delta.latency_p95_ms:.0f} ms")

    if args.write:
        name = stem(on_date, kind="rerank", label=args.label)
        command = " ".join(["python -m onboarding.evals.rerank", *sys.argv[1:]]).strip()
        summary, artifact = write_pair(
            args.out_dir,
            name,
            markdown=render(
                delta,
                command=command,
                commit=commit_hash(),
                environment=settings.environment,
                retrieval=retrieval_label(settings),
                artifact=f"{name}.jsonl",
                note=args.note.strip() or None,
                on_date=on_date,
            ),
            jsonl=_jsonl(records),
        )
        print(f"wrote {summary}")
        print(f"wrote {artifact}")
    return 1 if delta.failures else 0


if __name__ == "__main__":
    sys.exit(main())
