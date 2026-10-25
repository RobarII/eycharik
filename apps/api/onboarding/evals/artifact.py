"""What makes a measurement a measurement: a commit, a date, and a file.

Every evaluation writes the same pair — a markdown summary for the review and a JSONL artifact with
one case per line. The summary is prose; the commit line is evidence. A number without a commit
proves nothing, so the commit is resolved in one place instead of four.

A module that forks the resolution can record "unknown" while the others record a hash in the very
same run, and then the archive holds two versions of the same evening's truth.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]

# The login that answers for a measurement, as ``git shortlog`` spells it. A fork changes the
# constant; a run does not, because a document written by a tool must still name a person.
OWNER = "p4ulbr4dl3y"


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


def write_pair(out_dir: Path, name: str, *, markdown: str, jsonl: str) -> tuple[Path, Path]:
    """Write ``<name>.md`` and ``<name>.jsonl`` next to each other and return both paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = out_dir / f"{name}.jsonl"
    summary = out_dir / f"{name}.md"
    artifact.write_text(jsonl, encoding="utf-8")
    summary.write_text(markdown, encoding="utf-8")
    return summary, artifact


def frontmatter(
    title: str, summary: str, *, on_date: date, kind: str = "измерение", status: str = "принято"
) -> str:
    """The block ``scripts/check_docs.py`` requires, emitted by the writer that runs.

    ``--write`` used to produce a summary without a frontmatter, so the next run of the same
    command broke ``make docs`` until someone typed the block back. A generated document owns its
    own header.
    """
    block = {
        "title": title,
        "summary": summary,
        "kind": kind,
        "owner": OWNER,
        "status": status,
        "last_verified": on_date.isoformat(),
    }
    body = "\n".join(
        f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in block.items()
    )
    return f"---\n{body}\n---\n\n"
