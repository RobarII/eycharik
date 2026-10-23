"""Media type resolution for one upload.

A browser's ``Content-Type`` for a deck is unreliable: it is often
``application/octet-stream``. The file suffix decides for the formats this project reads; a declared
type is trusted only when it names a format the readers own. Nothing is sniffed from the bytes: a
PDF that claims to be a PPTX fails at the reader, with a reason, not with a guess.
"""

from __future__ import annotations

from pathlib import PurePosixPath

PDF = "application/pdf"
PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
PPSX = "application/vnd.openxmlformats-officedocument.presentationml.slideshow"

_BY_SUFFIX = {
    ".pdf": PDF,
    ".pptx": PPTX,
    ".ppsx": PPSX,
}
SUPPORTED = frozenset(_BY_SUFFIX.values())


def media_type_for(filename: str, declared: str | None = None) -> str:
    """Best known type for a filename, falling back to a trusted declared type."""
    suffix = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
    known = _BY_SUFFIX.get(suffix)
    if known is not None:
        return known
    normalized = (declared or "").split(";")[0].strip().lower()
    return normalized or "application/octet-stream"
