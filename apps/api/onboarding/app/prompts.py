"""Load a versioned prompt and its metadata.

A prompt is a file pair: ``<name>/v<version>.md`` and ``<name>/v<version>.meta.yaml``.
The version in the file name, the metadata, and the request must agree, so a trace can name
exactly what ran.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from onboarding.core.prompting import PromptError, render

MAX_PROMPT_BYTES = 64_000
_VERSION_FILE = re.compile(r"^v(\d+)\.md$")


class PromptNotFoundError(LookupError):
    """The requested prompt version has no file pair."""


@dataclass(frozen=True, slots=True)
class Prompt:
    name: str
    version: int
    template: str
    model: str
    temperature: float
    max_tokens: int | None = None

    def render(self, values: dict[str, str]) -> str:
        return render(self.template, values)


class PromptLibrary:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._cache: dict[tuple[str, int], Prompt] = {}

    def versions(self, name: str) -> tuple[int, ...]:
        """Every version on disk, ordered. The directory is the list; nothing is pinned twice."""
        directory = self._root / name
        if not directory.is_dir():
            raise PromptNotFoundError(f"missing prompt directory {directory}")
        found = sorted(
            int(match.group(1))
            for path in directory.iterdir()
            if (match := _VERSION_FILE.match(path.name)) and path.is_file()
        )
        if not found:
            raise PromptNotFoundError(f"{directory} holds no v<number>.md file")
        return tuple(found)

    def load_latest(self, name: str) -> Prompt:
        """The newest version is in force: publishing ``v8`` activates it, deleting it undoes."""
        return self.load(name, self.versions(name)[-1])

    def load(self, name: str, version: int) -> Prompt:
        key = (name, version)
        if key in self._cache:
            return self._cache[key]
        prompt = self._read(name, version)
        self._cache[key] = prompt
        return prompt

    def _read(self, name: str, version: int) -> Prompt:
        directory = self._root / name
        body_path = directory / f"v{version}.md"
        meta_path = directory / f"v{version}.meta.yaml"
        for path in (body_path, meta_path):
            if not path.is_file():
                raise PromptNotFoundError(f"missing prompt file {path}")
            if path.stat().st_size > MAX_PROMPT_BYTES:
                raise PromptError(f"{path} exceeds {MAX_PROMPT_BYTES} bytes")

        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
        if not isinstance(meta, dict):
            raise PromptError(f"{meta_path}: expected a mapping")
        _require(meta, "version", int, meta_path)
        _require(meta, "name", str, meta_path)
        _require(meta, "model", str, meta_path)
        if meta["version"] != version or meta["name"] != name:
            raise PromptError(
                f"{meta_path}: meta says {meta['name']} v{meta['version']}, "
                f"file says {name} v{version}"
            )
        temperature = meta.get("temperature", 0.2)
        if not isinstance(temperature, int | float):
            raise PromptError(f"{meta_path}: temperature must be a number")
        max_tokens = meta.get("max_tokens")
        if max_tokens is not None and not _is_int(max_tokens):
            raise PromptError(f"{meta_path}: max_tokens must be an integer")
        return Prompt(
            name=name,
            version=version,
            template=body_path.read_text(encoding="utf-8"),
            model=str(meta["model"]),
            temperature=float(temperature),
            max_tokens=max_tokens,
        )


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require(meta: dict[str, Any], key: str, expected: type, path: Path) -> None:
    value = meta.get(key)
    if not isinstance(value, expected) or isinstance(value, bool):
        raise PromptError(f"{path}: {key} must be {expected.__name__}")
