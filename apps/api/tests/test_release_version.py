from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "release_version.py"

spec = importlib.util.spec_from_file_location("release_version", SCRIPT)
assert spec is not None
assert spec.loader is not None
release_version = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_version)


@pytest.mark.parametrize("ref", ["v0.1.0", "v1.2.3", "v10.20.30"])
def test_a_release_tag_is_its_own_version(ref: str) -> None:
    assert release_version.version(ref) == ref


@pytest.mark.parametrize(
    "ref",
    [
        "main",
        "sha-0edf234",
        "v1.2",
        "v1.2.3-rc1",
        "1.2.3",
        "v01.2.3",
        "v1.2.3.4",
        "",
    ],
)
def test_anything_that_is_not_a_semantic_version_is_refused(ref: str) -> None:
    with pytest.raises(ValueError, match=r"vMAJOR\.MINOR\.PATCH"):
        release_version.version(ref)


def test_the_refusal_says_what_to_do_instead() -> None:
    with pytest.raises(ValueError, match="tag the commit instead"):
        release_version.version("main")


def test_the_command_prints_the_version_and_fails_on_a_branch() -> None:
    assert release_version.main(["--ref", "v2.0.0"]) == 0
    assert release_version.main(["--ref", "main"]) == 2
