"""Load a versioned Jev rubric and hold it to its contract.

A rubric is a prompt artifact like any other (ADR 0004), so it lives in
``docs/prompts/<name>/v<version>.yaml`` and a wording change is a new version, never an edit. Its
shape is owned by ``docs/contracts/jev-rubric.schema.json``; the meaning a schema cannot express —
the tone question must be a choice over the ``Sentiment`` enum, and every ``tag_*`` question must
name a ``SignalTag`` — is checked here, at startup, where a typo is a failed deploy.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from onboarding.core.models import Sentiment, SignalTag

MAX_RUBRIC_BYTES = 64_000
_SELECTOR = re.compile(r"^(?P<name>[a-z0-9][a-z0-9._-]*)@(?P<version>[1-9][0-9]*)$")
_TAGS = {tag.value: tag for tag in SignalTag}


class RubricError(ValueError):
    """The rubric is missing, oversized, or violates its contract."""


@dataclass(frozen=True, slots=True)
class RubricQuestion:
    type: str
    instructions: str
    criteria: tuple[str, ...] = ()

    def payload(self) -> dict[str, Any]:
        body: dict[str, Any] = {"type": self.type, "instructions": self.instructions}
        if self.criteria:
            body["criteria"] = list(self.criteria)
        return body


@dataclass(frozen=True, slots=True)
class Rubric:
    name: str
    version: int
    tag_threshold: float
    max_tags: int
    questions: dict[str, RubricQuestion]

    @property
    def selector(self) -> str:
        return f"{self.name}@{self.version}"

    @property
    def sentiment_criteria(self) -> tuple[str, ...]:
        return self.questions["sentiment"].criteria

    @property
    def tags(self) -> dict[str, SignalTag]:
        """Question name to signal tag, in file order. The adapter only ever asks these."""
        return {
            key: _TAGS[key.removeprefix("tag_")]
            for key in self.questions
            if key.startswith("tag_")
        }


def parse_selector(selector: str) -> tuple[str, int]:
    match = _SELECTOR.fullmatch(selector)
    if match is None:
        raise RubricError(f"rubric selector must be <name>@<version>, got {selector!r}")
    return match.group("name"), int(match.group("version"))


class RubricLibrary:
    """Read rubric files once and cache them. I/O lives here, never in the classifier."""

    def __init__(self, root: Path, schema_path: Path) -> None:
        self._root = root
        self._schema_path = schema_path
        self._validator: Draft202012Validator | None = None
        self._cache: dict[str, Rubric] = {}

    def load(self, selector: str) -> Rubric:
        if selector not in self._cache:
            name, version = parse_selector(selector)
            self._cache[selector] = self._read(name, version)
        return self._cache[selector]

    def _read(self, name: str, version: int) -> Rubric:
        path = self._root / name / f"v{version}.yaml"
        if not path.is_file():
            raise RubricError(f"missing rubric {path}")
        if path.stat().st_size > MAX_RUBRIC_BYTES:
            raise RubricError(f"{path} exceeds {MAX_RUBRIC_BYTES} bytes")
        payload = _payload(path)
        self._validate(payload, path)
        if payload.get("name") != name or payload.get("version") != version:
            raise RubricError(
                f"{path}: rubric says {payload.get('name')}@v{payload.get('version')}, "
                f"but the selector says {name}@v{version}"
            )
        questions = {
            key: RubricQuestion(
                type=str(value["type"]),
                instructions=str(value["instructions"]).strip(),
                criteria=tuple(str(item) for item in value.get("criteria", ())),
            )
            for key, value in payload["questions"].items()
        }
        rubric = Rubric(
            name=name,
            version=version,
            tag_threshold=float(payload["tag_threshold"]),
            max_tags=int(payload["max_tags"]),
            questions=questions,
        )
        _require_meaning(rubric, path)
        return rubric

    def _validate(self, payload: dict[str, Any], path: Path) -> None:
        failures = sorted(
            self._schema().iter_errors(payload), key=lambda failure: list(failure.path)
        )
        if failures:
            failure = failures[0]
            where = "/".join(str(part) for part in failure.path) or "rubric"
            raise RubricError(f"{path}: {where}: {failure.message}")

    def _schema(self) -> Draft202012Validator:
        if self._validator is None:
            schema = json.loads(self._schema_path.read_text(encoding="utf-8"))
            self._validator = Draft202012Validator(schema, format_checker=FormatChecker())
        return self._validator


def _payload(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise RubricError(f"{path}: not valid YAML: {error}") from None
    if not isinstance(payload, dict):
        raise RubricError(f"{path}: rubric must be a mapping")
    return payload


def _require_meaning(rubric: Rubric, path: Path) -> None:
    """The rules a schema cannot state: the tone question maps onto the enum, tags onto tags."""
    sentiment = rubric.questions.get("sentiment")
    if sentiment is None or sentiment.type != "choice":
        raise RubricError(f"{path}: a choice question named 'sentiment' is required")
    if set(sentiment.criteria) != {item.value for item in Sentiment}:
        raise RubricError(f"{path}: sentiment criteria must match the Sentiment enum")
    tags = [key for key in rubric.questions if key.startswith("tag_")]
    if not tags:
        raise RubricError(f"{path}: at least one tag question is required")
    for key in tags:
        if key.removeprefix("tag_") not in _TAGS:
            raise RubricError(f"{path}: {key}: unknown signal tag")
