"""Which prompt version runs is a fact about the files, not about the code.

A prompt is a versioned document (ADR 0009): publishing ``v8`` is how a new wording reaches
production, and the audit line must name the version that actually rendered. Both need the
directory to be the single list of versions, so the library reads it instead of being told.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from onboarding.app.prompts import PromptLibrary, PromptNotFoundError


def prompt_dir(tmp_path: Path, *versions: int) -> Path:
    root = tmp_path / "prompts"
    directory = root / "answer"
    directory.mkdir(parents=True)
    for version in versions:
        (directory / f"v{version}.md").write_text("Привет, {question}", encoding="utf-8")
        (directory / f"v{version}.meta.yaml").write_text(
            f"version: {version}\nname: answer\nmodel: m\ntemperature: 0.0\n",
            encoding="utf-8",
        )
    return root


def test_versions_are_sorted_numerically(tmp_path: Path) -> None:
    library = PromptLibrary(prompt_dir(tmp_path, 2, 10, 1))

    assert library.versions("answer") == (1, 2, 10)


def test_the_newest_version_is_the_one_in_force(tmp_path: Path) -> None:
    library = PromptLibrary(prompt_dir(tmp_path, 6, 7))

    assert library.load_latest("answer").version == 7


def test_an_unknown_version_is_a_lookup_error(tmp_path: Path) -> None:
    library = PromptLibrary(prompt_dir(tmp_path, 7))

    with pytest.raises(PromptNotFoundError, match="v8"):
        library.load("answer", 8)


def test_a_directory_without_prompts_is_not_silently_empty(tmp_path: Path) -> None:
    root = prompt_dir(tmp_path)
    (root / "answer" / "README.md").write_text("нет версий", encoding="utf-8")

    with pytest.raises(PromptNotFoundError, match=r"no v<number>\.md"):
        PromptLibrary(root).load_latest("answer")


def test_a_missing_directory_names_the_path(tmp_path: Path) -> None:
    with pytest.raises(PromptNotFoundError, match="prompt"):
        PromptLibrary(tmp_path / "prompts").load_latest("answer")


def test_the_real_prompt_set_loads_its_newest_answer_version() -> None:
    """The shipped corpus is not a fixture: the gate fails if the newest file has no pair."""
    root = Path(__file__).resolve().parents[3] / "docs" / "prompts"

    prompt = PromptLibrary(root).load_latest("answer")

    assert prompt.version == max(PromptLibrary(root).versions("answer"))
    assert "{context}" in prompt.template
