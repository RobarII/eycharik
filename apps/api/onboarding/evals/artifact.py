"""What makes a measurement a measurement: a commit, a date, and a file.

Every evaluation writes the same pair — a markdown summary for the review and a JSONL artifact with
one case per line. The summary is prose; the commit line is evidence. A number without a commit
proves nothing, so the commit is resolved in one place instead of four.

A module that forks the resolution can record "unknown" while the others record a hash in the very
same run, and then the archive holds two versions of the same evening's truth.
"""

from __future__ import annotations

import shutil
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def commit_hash(root: Path = ROOT) -> str:
    """Short HEAD, or ``"unknown"`` outside a checkout.

    ``git`` is resolved through ``PATH`` and run from the repository root, so the answer does not
    depend on which directory the operator happened to be in.
    """
    git = shutil.which("git")
    if git is None:
        return "unknown"
    try:
        return subprocess.run(  # noqa: S603 - resolved binary, fixed argv, no shell
            [git, "rev-parse", "--short", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def stem(on_date: date, *, kind: str, label: str = "") -> str:
    """``YYYY-MM-DD-eval-<kind>[-<label>]``: one name that sorts by date and reads as a command."""
    suffix = f"-{label.strip()}" if label.strip() else ""
    return f"{on_date.isoformat()}-eval-{kind}{suffix}"


def write_pair(
    out_dir: Path, name: str, *, markdown: str, jsonl: str
) -> tuple[Path, Path]:
    """Write ``<name>.md`` and ``<name>.jsonl`` next to each other and return both paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = out_dir / f"{name}.jsonl"
    summary = out_dir / f"{name}.md"
    artifact.write_text(jsonl, encoding="utf-8")
    summary.write_text(markdown, encoding="utf-8")
    return summary, artifact
