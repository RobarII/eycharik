"""Assemble a knowledge document from extracted text and recruiter-supplied metadata.

Extraction supplies the body; a human supplies ``id``, ``owner``, ``audience``, ``valid_from``.
Nothing is guessed: a missing field is a validation error, not a default. The assembled text goes
through the existing ``parse_document`` choke point, so an uploaded file is validated exactly like a
file in ``knowledge/`` — one contract, one place to enforce it.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import yaml

RESERVED = frozenset({"text"})


def render_document(metadata: Mapping[str, Any], body: str) -> str:
    """Frontmatter plus body, in the shape ``ingest.parse_document`` expects."""
    frontmatter = {key: value for key, value in metadata.items() if key not in RESERVED}
    if not frontmatter:
        raise ValueError(
            "document metadata is empty: id, owner, audience and valid_from are required"
        )
    # ``safe_dump`` sorts by default; insertion order keeps the file readable and diffable.
    dumped = yaml.safe_dump(
        frontmatter,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).strip()
    text = body.strip()
    if not text:
        raise ValueError("document body is empty")
    return f"---\n{dumped}\n---\n\n{text}\n"
