"""Audience and validity rules for knowledge retrieval.

The SQL layer applies the same rules before ranking; this module is the reference implementation
and the one covered by unit tests.
"""

from __future__ import annotations

from collections.abc import Collection
from datetime import date

from .models import Document

HR_ONLY = "hr_only"
EVERYONE = "all"


def permits(audience: Collection[str], viewer: Collection[str]) -> bool:
    """True when a viewer with these scopes may retrieve a chunk with this audience."""
    if not audience:
        return False
    if HR_ONLY in audience:
        return HR_ONLY in viewer
    if EVERYONE in audience:
        return True
    return bool(set(audience) & set(viewer))


def is_valid(document: Document, on_date: date) -> bool:
    if on_date < document.valid_from:
        return False
    return document.valid_to is None or on_date <= document.valid_to
