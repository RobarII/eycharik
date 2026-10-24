#!/usr/bin/env python3
"""Decide the version a release run publishes.

Two ways in, one rule each:

- a push to `main`: the next patch tag (`v0.1.3` -> `v0.1.4`) unless the commit is already
  tagged, in which case the run reuses that tag. Reusing the tag is what makes a re-run cheap and
  what keeps `version.json` stable for tabs that are already open;
- a tag push or a manual dispatch: the version is the ref itself, and the workflow creates no tag.

The version is what the image label, the git tag and the cabinet's `/version.json` all agree on,
so it is computed once, in a job of its own, and passed to the builders.

    python3 scripts/next_release.py --ref-type branch --ref-name main
    python3 scripts/next_release.py --ref-type tag --ref-name v0.1.4
    python3 scripts/next_release.py --ref-type dispatch --ref-name feature/x
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable, Sequence

TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")

Version = tuple[int, int, int]


def parse(tag: str) -> Version | None:
    """`v1.2.3` -> `(1, 2, 3)`; anything else is not a release tag and is ignored."""
    match = TAG.match(tag)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def releases(tags: Iterable[str]) -> list[Version]:
    parsed = (parse(tag) for tag in tags)
    return sorted(version for version in parsed if version is not None)


def bump_patch(tags: Iterable[str]) -> str:
    """The next patch release. No tags yet means the first release is `v0.1.0`."""
    known = releases(tags)
    if not known:
        return "v0.1.0"
    major, minor, patch = known[-1]
    return f"v{major}.{minor}.{patch + 1}"


def decide(*, ref_type: str, ref_name: str, tags: Iterable[str], at_head: Iterable[str]) -> str:
    """The version for this run, given the ref and the tags that already exist."""
    if ref_type != "branch" or ref_name != "main":
        return ref_name
    tagged = releases(at_head)
    if tagged:
        major, minor, patch = tagged[-1]
        return f"v{major}.{minor}.{patch}"
    return bump_patch(tags)


def _git(*args: str) -> list[str]:
    """Read the tags from the checkout; the workflow can also pass them in explicitly."""
    git = shutil.which("git")
    if git is None:
        raise SystemExit("git is not installed")
    output = subprocess.run(  # noqa: S603 - a fixed argument list, no shell
        (git, *args), check=True, capture_output=True, text=True
    ).stdout
    return [line.strip() for line in output.splitlines() if line.strip()]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref-type", required=True, choices=("branch", "tag", "dispatch"))
    parser.add_argument("--ref-name", required=True)
    parser.add_argument(
        "--tags",
        help="release tags, one per line; read from git when omitted",
    )
    parser.add_argument(
        "--at-head",
        help="release tags that point at HEAD, one per line; read from git when omitted",
    )
    options = parser.parse_args(argv)

    tags = options.tags.split() if options.tags is not None else _git("tag", "--list", "v[0-9]*")
    at_head = (
        options.at_head.split()
        if options.at_head is not None
        else _git("tag", "--points-at", "HEAD", "--list", "v[0-9]*")
    )
    version = decide(
        ref_type=options.ref_type, ref_name=options.ref_name, tags=tags, at_head=at_head
    )
    print(version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
