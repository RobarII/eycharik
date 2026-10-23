"""Extraction profiles: how to read a file, as data.

The same shape as model profiles (ADR 0013). One YAML per profile, validated against
``docs/contracts/extraction-profile.schema.json`` at startup, so a broken profile is a deployment
error rather than a surprise when HR uploads a scan. ``family`` names the recognizer; the
composition root turns it into a class, and no code below that branches on it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from onboarding.core.models import AcceptancePolicy, QualityPolicy
from onboarding.ports import ExtractionProfile

ROLE = "extract"
MAX_PROFILE_BYTES = 8_000
_NAME = re.compile(r"[a-z0-9][a-z0-9._-]*")


class ExtractionProfileError(ValueError):
    """The profile file is missing, oversized, or violates its contract."""


class ExtractionProfileLibrary:
    """Read profile files once. I/O lives here; the router only ever sees values."""

    def __init__(self, root: Path, schema_path: Path) -> None:
        self._root = root
        self._schema_path = schema_path
        self._validator: Draft202012Validator | None = None
        self._cache: dict[str, ExtractionProfile] = {}

    def load(self, name: str) -> ExtractionProfile:
        if name not in self._cache:
            self._cache[name] = _profile(self._read(name), source=name)
        return self._cache[name]

    def available(self) -> tuple[str, ...]:
        if not self._root.is_dir():
            return ()
        return tuple(sorted(path.stem for path in self._root.glob("*.yaml")))

    def _read(self, name: str) -> dict[str, Any]:
        if not _NAME.fullmatch(name):
            raise ExtractionProfileError(f"invalid extraction profile name {name!r}")
        path = self._root / f"{name}.yaml"
        if not path.is_file():
            known = ", ".join(self.available()) or "none"
            raise ExtractionProfileError(
                f"missing extraction profile {path} (known profiles: {known})"
            )
        if path.stat().st_size > MAX_PROFILE_BYTES:
            raise ExtractionProfileError(f"{path} exceeds {MAX_PROFILE_BYTES} bytes")
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            raise ExtractionProfileError(f"{path}: not valid YAML: {error}") from None
        if not isinstance(data, dict):
            raise ExtractionProfileError(f"{path}: expected a mapping")
        if data.get("name") != name:
            raise ExtractionProfileError(
                f"{path}: name is {data.get('name')!r}, but the file is {name}.yaml"
            )
        failures = sorted(
            self._contract().iter_errors(data), key=lambda failure: list(failure.path)
        )
        if failures:
            failure = failures[0]
            where = "/".join(str(part) for part in failure.path) or "profile"
            raise ExtractionProfileError(f"{path}: {where}: {failure.message}")
        return data

    def _contract(self) -> Draft202012Validator:
        if self._validator is None:
            schema: Any = json.loads(self._schema_path.read_text(encoding="utf-8"))
            self._validator = Draft202012Validator(schema, format_checker=FormatChecker())
        return self._validator


def _profile(data: dict[str, Any], *, source: str) -> ExtractionProfile:
    quality = _mapping(data.get("quality"), source=source, field="quality")
    acceptance = _mapping(data.get("acceptance"), source=source, field="acceptance")
    return ExtractionProfile(
        name=str(data["name"]),
        family=cast(Any, str(data["family"])),
        model=str(data.get("model", "")),
        lang=str(data.get("lang", "ru")),
        dpi=int(data.get("dpi", 300)),
        min_text_chars=int(data.get("min_text_chars", 40)),
        quality=QualityPolicy(
            min_dpi=_optional_int(quality.get("min_dpi")),
            min_edge_energy=_optional_float(quality.get("min_edge_energy")),
        ),
        acceptance=AcceptancePolicy(
            min_confidence=float(acceptance.get("min_confidence", 0.72)),
            min_chars=int(acceptance.get("min_chars", 40)),
        ),
    )


def _mapping(value: Any, *, source: str, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ExtractionProfileError(f"{source}: {field} must be a mapping")
    return value


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)
