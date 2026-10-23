"""Documentation hygiene: the index is complete and every link resolves.

A docs tree without an index is a pile of files. This check keeps `docs/README.md` honest and
catches a rename that left a dead link behind.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs"
INDEX = DOCS / "README.md"
LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

SKIP = {"README.md"}


def main() -> int:
    problems: list[str] = []
    index_text = INDEX.read_text(encoding="utf-8")
    linked = {
        (INDEX.parent / target).resolve()
        for target in LINK.findall(index_text)
        if not target.startswith(("http://", "https://", "#"))
    }

    for path in sorted(DOCS.rglob("*.md")):
        if path.name in SKIP or path.parent.name in {"measurements", "incidents"}:
            continue
        if path.resolve() not in linked:
            problems.append(f"not in docs/README.md: {path.relative_to(DOCS.parent)}")

    for path in sorted(DOCS.rglob("*.md")):
        for target in LINK.findall(path.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            destination = (path.parent / target.split("#")[0]).resolve()
            if not destination.exists():
                problems.append(
                    f"dead link in {path.relative_to(DOCS.parent)}: {target}"
                )

    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print(f"docs ok: {len(list(DOCS.rglob('*.md')))} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
