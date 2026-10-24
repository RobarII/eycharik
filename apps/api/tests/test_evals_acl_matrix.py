"""The ACL matrix has to cover the corpus, not the pairs someone remembered.

Ten hand-written cases prove the predicate works for ten pairs. One viewer without a case, or one
document missing from the matrix, is the pair that leaks.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from onboarding.app.knowledge.ingest import load_corpus
from onboarding.app.settings import Settings
from onboarding.evals import acl
from onboarding.evals.acl import (
    VIEWERS,
    CorpusDocument,
    audiences_in,
    build_cases,
    principal_audiences,
    visible,
)
from onboarding.evals.artifact import commit_hash
from onboarding.evals.runner import Report

from .fakes import FakeKnowledgeBase

ROOT = Path(__file__).resolve().parents[3]

ON_DATE = date(2026, 10, 24)

DOCS = (
    CorpusDocument("hr/leave-policy", "Отпуска и отгулы", ("all",), "Отпуск 28 календарных дней"),
    CorpusDocument("hr/salary-bands", "Вилки окладов", ("hr_only",), "Вилки окладов по грейдам"),
    CorpusDocument("it/vpn", "VPN", ("dept:it",), "Подключение к VPN через клиент"),
    CorpusDocument(
        "hr/leave-policy-2025",
        "Отпуска и отгулы (редакция 2025)",
        ("all",),
        "Отпуск 24 календарных дня",
        valid_from=date(2025, 1, 1),
        valid_to=date(2025, 12, 31),
    ),
)


def test_a_viewer_carries_the_shared_corpus_and_its_own_audience() -> None:
    assert principal_audiences("all") == ("all",)
    assert principal_audiences("dept:it") == ("all", "dept:it")


def test_visibility_is_an_overlap_between_two_audience_sets() -> None:
    assert visible("all", ("all",))
    assert visible("dept:it", ("dept:it",))
    assert not visible("dept:sales", ("dept:it",))
    assert visible("hr_only", ("all",))


def test_the_matrix_holds_one_case_per_pair() -> None:
    cases = build_cases(DOCS, ON_DATE)

    assert len(cases) == len(DOCS) * len(VIEWERS)
    assert len({case.id for case in cases}) == len(cases)


def test_a_forbidden_document_is_guarded_and_an_allowed_one_is_expected() -> None:
    cases = {case.id: case for case in build_cases(DOCS, ON_DATE)}

    hidden = cases["acl-all-hr-salary-bands"]
    assert hidden.expect_docs == ()
    assert "hr/salary-bands" in hidden.expect_absent_docs

    shared = cases["acl-all-hr-leave-policy"]
    assert shared.expect_docs == ("hr/leave-policy",)
    assert "hr/salary-bands" in shared.expect_absent_docs


def test_an_expired_edition_is_invisible_to_every_viewer() -> None:
    cases = {case.id: case for case in build_cases(DOCS, ON_DATE)}

    for viewer in VIEWERS:
        case = cases[f"acl-{viewer.replace(':', '-')}-hr-leave-policy-2025"]
        assert case.expect_docs == ()
        assert "hr/leave-policy-2025" in case.expect_absent_docs


def test_the_question_is_text_the_document_contains() -> None:
    cases = {case.id: case for case in build_cases(DOCS, ON_DATE)}

    assert cases["acl-all-it-vpn"].question.startswith("Подключение к VPN")


def test_a_department_sees_its_own_document() -> None:
    cases = {case.id: case for case in build_cases(DOCS, ON_DATE)}

    assert cases["acl-dept-it-it-vpn"].expect_docs == ("it/vpn",)
    assert "it/vpn" in cases["acl-dept-sales-it-vpn"].expect_absent_docs


def test_every_audience_the_corpus_names_has_a_viewer() -> None:
    settings = Settings(_env_file=None, embed_provider="hashing", embed_dim=1024)
    corpus = load_corpus(
        settings.knowledge_dir,
        settings.contracts_dir / "doc.schema.json",
    )
    documents = tuple(
        CorpusDocument(
            doc_id=str(loaded.document.id),
            title=loaded.document.title,
            audience=tuple(loaded.document.audience),
        )
        for loaded in corpus
        if loaded.status == "active"
    )

    assert audiences_in(documents) <= set(VIEWERS), (
        "a new audience reached knowledge/ without a viewer in the ACL matrix"
    )


def test_the_question_is_the_first_readable_line_of_the_body() -> None:
    text = "# Отпуска\n\nЕжегодный оплачиваемый отпуск — 28 календарных дней."

    assert acl._question(text) == "Ежегодный оплачиваемый отпуск — 28 календарных дней."


def test_the_loaded_corpus_carries_a_question_for_every_document() -> None:
    documents = acl.loaded_documents(Settings(_env_file=None, embed_provider="hashing"))

    assert documents
    assert all(document.question.strip() for document in documents)
    assert all(document.audience for document in documents)


def test_a_corpus_without_documents_is_a_refusal_not_an_empty_report(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(acl, "loaded_documents", lambda settings: ())

    assert acl.main([]) == 2
    assert "no active documents" in capsys.readouterr().err


def test_an_audience_without_a_viewer_stops_the_matrix(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        acl,
        "loaded_documents",
        lambda settings: (CorpusDocument("hr/x", "X", ("dept:legal",), "текст документа"),),
    )

    assert acl.main([]) == 2
    assert "audiences without a viewer" in capsys.readouterr().err


def test_a_pass_renders_and_writes_its_measurement(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class Container:
        knowledge = FakeKnowledgeBase(chunks=())

        async def aclose(self) -> None:
            return None

    async def passing_run(
        cases: tuple[object, ...], knowledge: object, *, on_date: date
    ) -> Report:
        # The wiring test lives in ``test_eval_harness``: here only the artifact is under test.
        del cases, knowledge, on_date
        return Report(
            metrics={"recall_at_5": 1.0, "mrr": 1.0, "leak_rate": 0.0},
            results=(),
            generated=False,
        )

    monkeypatch.setattr(acl, "build_container", lambda _settings: Container())
    monkeypatch.setattr(acl, "run", passing_run)

    code = acl.main(["--write", "--out-dir", str(tmp_path), "--label", "unit"])

    assert code == 0
    written = sorted(path.name for path in tmp_path.iterdir())
    assert len(written) == 2
    assert any(name.endswith(".jsonl") for name in written)


def test_the_commit_is_a_short_sha_or_the_honest_unknown() -> None:
    commit = commit_hash()

    valid = len(commit) == 7 and all(char in "0123456789abcdef" for char in commit)
    assert commit == "unknown" or valid
