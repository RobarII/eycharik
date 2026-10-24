from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "next_release.py"

spec = importlib.util.spec_from_file_location("next_release", SCRIPT)
assert spec is not None
assert spec.loader is not None
next_release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(next_release)


def test_a_push_to_main_tags_the_next_patch() -> None:
    version = next_release.decide(
        ref_type="branch",
        ref_name="main",
        tags=["v0.1.0", "v0.1.3", "v0.1.1"],
        at_head=[],
    )

    assert version == "v0.1.4"


def test_the_highest_tag_wins_and_not_the_last_one_git_prints() -> None:
    version = next_release.bump_patch(["v0.1.9", "v0.10.0", "v0.2.3"])

    assert version == "v0.10.1"


def test_tags_that_are_not_releases_are_ignored() -> None:
    version = next_release.bump_patch(["nightly", "v0.1", "sha-b65bab1", "v0.1.2"])

    assert version == "v0.1.3"


def test_the_first_release_starts_at_zero_one() -> None:
    assert next_release.bump_patch([]) == "v0.1.0"


def test_an_already_tagged_commit_reuses_its_tag() -> None:
    """A re-run must not publish `v0.1.4` and then `v0.1.5` for the same code."""
    version = next_release.decide(
        ref_type="branch",
        ref_name="main",
        tags=["v0.1.3", "v0.1.4"],
        at_head=["v0.1.4"],
    )

    assert version == "v0.1.4"


def test_a_tag_push_publishes_the_ref_it_was_given() -> None:
    version = next_release.decide(
        ref_type="tag",
        ref_name="v0.1.4",
        tags=["v0.1.3"],
        at_head=[],
    )

    assert version == "v0.1.4"


def test_a_dispatch_releases_the_ref_it_was_given() -> None:
    version = next_release.decide(
        ref_type="dispatch",
        ref_name="main",
        tags=["v0.1.3"],
        at_head=["v0.1.3"],
    )

    assert version == "main"


@pytest.mark.parametrize("ref_name", ["feature/knowledge-editor", "b65bab1"])
def test_a_manual_dispatch_publishes_the_ref_and_creates_no_tag(ref_name: str) -> None:
    version = next_release.decide(
        ref_type="branch",
        ref_name=ref_name,
        tags=["v0.1.3"],
        at_head=["v0.1.3"],
    )

    assert version == ref_name


def test_the_cli_reads_the_ref_from_its_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = next_release.main(
        [
            "--ref-type",
            "branch",
            "--ref-name",
            "main",
            "--tags",
            "v0.1.3",
            "--at-head",
            "",
        ]
    )

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "v0.1.4"
