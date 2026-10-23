"""Bundled scenario images and their MAX attachment shape.

A scenario names an asset, never a path. The adapter resolves the name inside one directory, so a
hand-edited YAML or a tampered outbox row cannot read an arbitrary file from the host.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

SUPPORTED_SUFFIXES = frozenset({".jpg", ".jpeg", ".png"})


class ImageAssetError(RuntimeError):
    """The named scenario image cannot be sent."""


def asset_path(directory: Path | None, name: str) -> Path:
    """Resolve one bundled image or raise when it is absent or escapes the asset directory."""
    if directory is None:
        raise ImageAssetError("scenario image assets are not configured")
    candidate = Path(name)
    if candidate.name != name or candidate.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ImageAssetError(f"unsupported scenario image name {name!r}")
    root = directory.resolve()
    path = (root / name).resolve()
    if path.parent != root:
        raise ImageAssetError(f"scenario image {name!r} escapes the asset directory")
    if not path.is_file():
        raise ImageAssetError(f"scenario image {name!r} is missing")
    return path


def image_attachment(token: str) -> dict[str, Any]:
    """One MAX image attachment. The token comes from ``POST /uploads``."""
    return {"type": "image", "payload": {"token": token}}


def content_type(path: Path) -> str:
    return "image/png" if path.suffix.lower() == ".png" else "image/jpeg"


def upload_token(payload: dict[str, Any]) -> str | None:
    """Read the media token from either documented upload response shape."""
    direct = payload.get("token")
    if isinstance(direct, str) and direct:
        return direct
    photos = payload.get("photos")
    if isinstance(photos, dict):
        ids = photos.get("photoIds")
        if isinstance(ids, dict):
            nested = ids.get("token")
            if isinstance(nested, str) and nested:
                return nested
        items = photos.get("photos")
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    nested = item.get("token")
                    if isinstance(nested, str) and nested:
                        return nested
    return None
