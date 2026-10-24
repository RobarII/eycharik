"""The eval command line: what it refuses before the database, what it writes after.

A quality run is only reproducible if the flags mean what they say and the artifact carries the
command, the commit, and the case table. Both are cheap to prove on a fake knowledge base, and a
mistake in either makes a measurement unreadable rather than wrong — which is worse.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from onboarding.evals import __main__ as cli
from onboarding.evals.runner import Case

from .fakes import scored_chunk


def args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "retrieval_only": True,
        "baseline": None,
        "compare": None,
        "write": False,
        "write_baseline": False,
        "fail_on_regression": False,
        "force_baseline": False,
        "out_dir": Path("docs/measurements"),
        "label": "test",
        "note": "",
        "limit": 0,
        "only": "",
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def case(case_id: str = "leave-28-days") -> Case:
    return Case(
        id=case_id,
        question="Сколько дней отпуска?",
        audience="all",
        expect_docs=("hr/leave-policy",),
        expect_contains=(),
        expect_escalation=False,
        expect_reason=None,
        stratum="fact",
    )


class Knowledge:
    def __init__(self, chunks: tuple[object, ...]) -> None:
        self._chunks = chunks

    async def search(self, query: object) -> tuple[object, ...]:
        del query
        return self._chunks


class FakeContainer:
    def __init__(self, chunks: tuple[object, ...] = ()) -> None:
        self.knowledge = Knowledge(chunks or (scored_chunk(),))
        self.closed = 0

    async def aclose(self) -> None:
        self.closed += 1


async def test_a_retrieval_run_passes_and_closes_its_container(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = FakeContainer()
    monkeypatch.setattr(cli, "build_container", lambda settings: fake)

    code = await cli._run(args(), (case(),))

    assert code == 0
    assert fake.closed == 1
    assert "recall_at_5" in capsys.readouterr().out


async def test_an_empty_knowledge_base_stops_before_the_report(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = FakeContainer()
    fake.knowledge = Knowledge(())  # type: ignore[assignment]
    monkeypatch.setattr(cli, "build_container", lambda settings: fake)

    code = await cli._run(args(), (case(),))

    assert code == 2
    assert fake.closed == 1
    assert "knowledge base is empty" in capsys.readouterr().err


async def test_write_names_the_artifact_and_names_the_case_in_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake = FakeContainer()
    monkeypatch.setattr(cli, "build_container", lambda settings: fake)

    code = await cli._run(
        args(write=True, out_dir=tmp_path, label="unit"), (case(),)
    )

    assert code == 0
    written = sorted(path.name for path in tmp_path.iterdir())
    assert len(written) == 2
    markdown = tmp_path / next(name for name in written if name.endswith(".md"))
    artifact = tmp_path / next(name for name in written if name.endswith(".jsonl"))
    body = markdown.read_text(encoding="utf-8")
    assert "- кейсов: 1" in body
    assert "onboarding.evals" in body
    assert "leave-28-days" in artifact.read_text(encoding="utf-8")


class ProbeThenEmpty:
    """The probe sees a chunk; the case retrieves nothing, so `recall_at_5` cannot pass."""

    def __init__(self) -> None:
        self.calls = 0

    async def search(self, query: object) -> tuple[object, ...]:
        del query
        self.calls += 1
        return (scored_chunk(),) if self.calls == 1 else ()


async def test_a_failing_gate_is_a_non_zero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeContainer()
    fake.knowledge = ProbeThenEmpty()  # type: ignore[assignment]
    monkeypatch.setattr(cli, "build_container", lambda settings: fake)

    code = await cli._run(args(), (case(),))

    assert code == 1


async def test_generation_is_refused_without_a_provider_key(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    original = cli.Settings
    monkeypatch.setattr(cli, "Settings", lambda: original(_env_file=None, llm_api_key=""))

    code = await cli._run(args(retrieval_only=False), (case(),))

    assert code == 2
    assert "LLM_API_KEY is not set" in capsys.readouterr().err


def test_the_limit_and_the_only_filter_narrow_the_set(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, ...]] = []

    async def fake_run(resolved: argparse.Namespace, cases: tuple[Case, ...]) -> int:
        del resolved
        seen.append(tuple(item.id for item in cases))
        return 0

    monkeypatch.setattr(cli, "_run", fake_run)
    all_cases = cli.load_cases(Path("docs/evals/golden.yaml"))

    cli.main(["--retrieval-only", "--limit", "1"])
    cli.main(["--retrieval-only", "--only", all_cases[0].id])

    assert seen == [(all_cases[0].id,), (all_cases[0].id,)]


def test_an_unknown_case_id_fails_before_any_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[object] = []

    async def fake_run(resolved: argparse.Namespace, cases: tuple[Case, ...]) -> int:
        called.append(cases)
        return 0

    monkeypatch.setattr(cli, "_run", fake_run)

    assert cli.main(["--only", "no-such-case"]) == 2
    assert called == []
