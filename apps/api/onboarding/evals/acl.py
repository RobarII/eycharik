"""The ACL matrix: every document, every viewer, one question each.

The golden set carries a handful of hand-written ACL cases, which is enough to notice that the
predicate is broken in the direction someone thought of. The predicate itself is a single SQL
clause shared by both retrievers, so the set that proves it should be the corpus, not a sample:
one case per (viewer, document) pair, with two ways to fail.

- a document the viewer must not see appears in the top 5 — a leak;
- a document the viewer may see does not appear — an over-restriction, which is quieter and just
  as wrong, because the assistant then refuses a question it should answer.

The run is retrieval-only: no provider key, no generation, no cost. ``recall_at_5`` and
``leak_rate`` are the two metrics that matter, and both are gated.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from onboarding.app.container import build_container
from onboarding.app.knowledge.ingest import load_corpus
from onboarding.app.settings import Settings
from onboarding.core.access import Subject, holds, permits, predicates
from onboarding.evals.artifact import commit_hash
from onboarding.evals.runner import (
    Case,
    Report,
    evaluate,
    render_markdown,
    summarise,
    write_jsonl,
)
from onboarding.ports import KnowledgeBase

ROOT = Path(__file__).resolve().parents[4]

# One viewer per audience the corpus can name, plus ``all``. A viewer is a principal: the profile
# builder turns ``dept:sales`` into ``("all", "dept:sales")``, so a department sees the shared
# corpus and its own documents, and nothing else.
VIEWERS: tuple[str, ...] = ("all", "hr_only", "dept:it", "dept:sales", "dept:production")


@dataclass(frozen=True, slots=True)
class CorpusDocument:
    doc_id: str
    title: str
    audience: tuple[str, ...]
    # The question is a sentence from the document, not its title. A title is a legitimate query,
    # but a title-only matrix measures relevance: ``company/about`` is short and generic, and no
    # ACL predicate should be blamed for the reranker not liking it.
    question: str = ""
    valid_from: date | None = None
    valid_to: date | None = None


def principal_audiences(viewer: str) -> tuple[str, ...]:
    return ("all",) if viewer == "all" else ("all", viewer)


def visible(viewer: str, audience: Sequence[str]) -> bool:
    """The audience half of the rule in ``core.access``, for callers that carry no date."""
    return permits(audience, principal_audiences(viewer))


def allowed(viewer: str, document: CorpusDocument, on_date: date) -> bool:
    """The whole rule: audience, status and validity, evaluated by the module that owns it."""
    return holds(
        predicates(principal_audiences(viewer), on_date),
        Subject(
            audience=tuple(document.audience),
            valid_from=document.valid_from,
            valid_to=document.valid_to,
        ),
    )


def build_cases(documents: Sequence[CorpusDocument], on_date: date) -> tuple[Case, ...]:
    """One case per (viewer, document). A case is guarded when the pair must not match.

    Visibility has two halves: the audience overlap and the validity window. An expired edition is
    invisible to everyone, so it belongs in the guard list of every viewer — that is the leak the
    golden set already trapped by hand, and the matrix traps it 345 times.
    """
    cases: list[Case] = []
    for viewer in VIEWERS:
        for document in documents:
            admitted = allowed(viewer, document, on_date)
            forbidden = tuple(
                other.doc_id for other in documents if not allowed(viewer, other, on_date)
            )
            cases.append(
                Case(
                    id=f"acl-{viewer.replace(':', '-')}-{document.doc_id.replace('/', '-')}",
                    question=document.question or document.title,
                    audience=viewer,
                    expect_docs=(document.doc_id,) if admitted else (),
                    expect_contains=(),
                    expect_escalation=False,
                    expect_reason=None,
                    expect_absent_docs=forbidden,
                    stratum="acl",
                )
            )
    return tuple(cases)


def loaded_documents(settings: Settings) -> tuple[CorpusDocument, ...]:
    corpus = load_corpus(
        settings.knowledge_dir,
        settings.contracts_dir / "doc.schema.json",
    )
    return tuple(
        CorpusDocument(
            doc_id=str(loaded.document.id),
            title=loaded.document.title,
            audience=tuple(loaded.document.audience),
            question=_question(loaded.document.text),
            valid_from=loaded.document.valid_from,
            valid_to=loaded.document.valid_to,
        )
        for loaded in corpus
        if loaded.status == "active"
    )


def _question(text: str, *, limit: int = 120) -> str:
    """The first line of the body: text the document itself contains, so a miss is not relevance."""
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if len(stripped.split()) >= 3:
            return stripped[:limit]
    return text.strip()[:limit]


def audiences_in(documents: Sequence[CorpusDocument]) -> set[str]:
    return {audience for document in documents for audience in document.audience} - {"all"}


async def run(cases: tuple[Case, ...], knowledge: KnowledgeBase, *, on_date: date) -> Report:
    """Score a case list against any knowledge backend: the matrix is a library, not a script."""
    results = await evaluate(cases, knowledge=knowledge, answerer=None, on_date=on_date)
    return summarise(results, generated=False)


def matrix(documents: Sequence[CorpusDocument], *, on_date: date) -> tuple[Case, ...]:
    """The whole matrix, built offline: the cases depend on the corpus, not on a connection."""
    return build_cases(documents, on_date)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="onboarding.evals.acl")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "docs" / "measurements")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--label", default="acl-matrix")
    parser.add_argument("--note", default="")
    args = parser.parse_args(argv)

    settings = Settings()
    documents = loaded_documents(settings)
    if not documents:
        print("no active documents; run `make ingest` first", file=sys.stderr)
        return 2
    missing = audiences_in(documents) - set(VIEWERS)
    if missing:
        print(f"corpus names audiences without a viewer: {sorted(missing)}", file=sys.stderr)
        return 2

    on_date = datetime.now(UTC).date()
    cases = matrix(documents, on_date=on_date)
    report = asyncio.run(_run_against_the_database(cases, settings, on_date))
    print(f"cases: {len(cases)} ({len(documents)} documents x {len(VIEWERS)} viewers)")
    print(f"recall_at_5: {report.metrics.get('recall_at_5', 0.0):.3f}")
    print(f"leak_rate:   {report.metrics.get('leak_rate', 0.0):.3f}")
    leaks = [result for result in report.results if result.leaked]
    for result in leaks[:20]:
        print(
            f"  leak {result.case.id}: saw {', '.join(result.leaked_docs)}",
            file=sys.stderr,
        )
    if args.write:
        _write(report, args, settings, on_date)
    return 1 if report.failures else 0


async def _run_against_the_database(
    cases: tuple[Case, ...], settings: Settings, on_date: date
) -> Report:
    """The only place the matrix touches a container: cases need a corpus, corpus needs a link."""
    container = build_container(settings)
    try:
        return await run(cases, container.knowledge, on_date=on_date)
    finally:
        await container.aclose()


def _write(report: Report, args: argparse.Namespace, settings: Settings, on_date: date) -> None:
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{on_date.isoformat()}-eval-retrieval-{args.label}"
    path = args.out_dir / f"{stem}.md"
    artifact = args.out_dir / f"{stem}.jsonl"
    write_jsonl(report, artifact)
    path.write_text(
        render_markdown(
            report,
            command=" ".join(["python -m onboarding.evals.acl", *sys.argv[1:]]).strip(),
            commit=commit_hash(),
            model="n/a",
            environment=settings.environment,
            embed_provider=settings.embed_provider,
            note=args.note.strip()
            or "every (viewer, document) pair; recall is over-restriction, leak_rate is disclosure",
            on_date=on_date,
            artifact=artifact.name,
        ),
        encoding="utf-8",
    )
    print(f"wrote {path}")
    print(f"wrote {artifact}")


if __name__ == "__main__":
    sys.exit(main())
