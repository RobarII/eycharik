#!/usr/bin/env python3
"""Decide and validate the version a release promotes to.

A version is a human decision, not a counter: the release workflow promotes the digest of a commit
that `main` already built, and the version comes from the ref the human pushed. The script exists so
that the rule is testable and the failure message names the rule, instead of a bare regex in YAML.

    python3 scripts/release_version.py --ref v1.2.3     # prints v1.2.3
    python3 scripts/release_version.py --ref main        # exits non-zero

Semantic versioning: `vMAJOR.MINOR.PATCH`, nothing else. Pre-release suffixes are not supported
because the deploy consumes the same tag, and a suffix would make "what is in production" ambiguous.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence

TAG = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def version(ref: str) -> str:
    """The version a ref promotes to, or `ValueError` naming every rule the ref breaks."""
    match = TAG.match(ref)
    if match is None:
        raise ValueError(
            f"{ref!r} is not a release version: use vMAJOR.MINOR.PATCH, e.g. v1.2.3. "
            "A branch cannot be promoted; tag the commit instead."
        )
    return ref


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", required=True, help="the ref being released: v1.2.3")
    options = parser.parse_args(argv)
    try:
        print(version(options.ref))
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
