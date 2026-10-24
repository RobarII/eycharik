"""The labelled sentiment set: what a case is, and what makes a set readable.

A case names the label, the tags and the split. The split matters: ``dev`` is where a rule is tuned,
``test`` is where it is judged, and a provider that looks good on ``dev`` only has learned the set.

The loader refuses a set it cannot trust — a wrong version, a duplicate id, the same text under two
labels, an unknown tag — because a quiet default in an evaluation turns into a green gate that means
nothing. Nothing here talks to a model or a database.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from onboarding.core.models import Sentiment, SignalTag

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CASES = ROOT / "docs" / "evals" / "sentiment.yaml"
SPLITS = ("dev", "test", "all")
SET_VERSION = 2
MAX_TAGS_PER_CASE = 3


class SentimentSetError(ValueError):
    """The labeled set does not satisfy the schema this runner reads."""


@dataclass(frozen=True, slots=True)
class Case:
    id: str
    text: str
    sentiment: Sentiment
    tags: tuple[SignalTag, ...]
    split: Literal["dev", "test"] = "dev"
    expect_escalation: bool = False
    note: str = ""


def load_cases(path: Path, *, split: str = "all") -> tuple[Case, ...]:
    if not path.is_file():
        raise SentimentSetError(f"missing sentiment set {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise SentimentSetError(f"{path}: expected a cases list")
    version = payload.get("version", 1)
    if version != SET_VERSION:
        raise SentimentSetError(f"{path}: version must be {SET_VERSION}, got {version!r}")
    cases: list[Case] = []
    seen: set[str] = set()
    for item in payload["cases"]:
        case = _case(item, path, seen)
        if split in ("all", case.split):
            cases.append(case)
    if not cases:
        raise SentimentSetError(f"{path}: no cases for split {split!r}")
    dupes = _duplicate_texts(cases)
    if dupes:
        raise SentimentSetError(f"{path}: duplicate case text: {', '.join(sorted(dupes))}")
    return tuple(cases)
def _case(item: Any, path: Path, seen: set[str]) -> Case:
    if not isinstance(item, dict):
        raise SentimentSetError(f"{path}: every case must be a mapping")
    case_id = item.get("id")
    text = item.get("text")
    if not isinstance(case_id, str) or not case_id or case_id in seen:
        raise SentimentSetError(f"{path}: id must be a unique non-empty string")
    if not isinstance(text, str) or not text.strip():
        raise SentimentSetError(f"{path}: {case_id}: text must be a non-empty string")
    try:
        sentiment = Sentiment(str(item.get("sentiment")))
    except ValueError:
        raise SentimentSetError(f"{path}: {case_id}: unknown sentiment") from None
    tags = _tags(item.get("tags", []), case_id, path)
    split = item.get("split", "dev")
    if split not in {"dev", "test"}:
        raise SentimentSetError(f"{path}: {case_id}: split must be 'dev' or 'test'")
    escalate = item.get("expect_escalation", False)
    if not isinstance(escalate, bool):
        raise SentimentSetError(f"{path}: {case_id}: expect_escalation must be a boolean")
    if escalate and sentiment is not Sentiment.NEGATIVE:
        raise SentimentSetError(
            f"{path}: {case_id}: a crisis case must be labelled negative, got {sentiment.value}"
        )
    note = item.get("note", "")
    if not isinstance(note, str):
        raise SentimentSetError(f"{path}: {case_id}: note must be a string")
    seen.add(case_id)
    return Case(
        id=case_id,
        text=text,
        sentiment=sentiment,
        tags=tags,
        split=split,
        expect_escalation=escalate,
        note=note,
    )
def _tags(raw: Any, case_id: str, path: Path) -> tuple[SignalTag, ...]:
    if not isinstance(raw, list):
        raise SentimentSetError(f"{path}: {case_id}: tags must be a list")
    tags: list[SignalTag] = []
    for item in raw:
        try:
            tag = SignalTag(str(item))
        except ValueError:
            raise SentimentSetError(f"{path}: {case_id}: unknown tag {item!r}") from None
        if tag in tags:
            raise SentimentSetError(f"{path}: {case_id}: duplicate tag {tag.value}")
        tags.append(tag)
    if len(tags) > MAX_TAGS_PER_CASE:
        raise SentimentSetError(
            f"{path}: {case_id}: at most {MAX_TAGS_PER_CASE} tags, "
            "the classifier cannot return more"
        )
    return tuple(tags)
def _duplicate_texts(cases: list[Case]) -> set[str]:
    seen: dict[str, str] = {}
    dupes: set[str] = set()
    for case in cases:
        normalized = " ".join(case.text.lower().split())
        if normalized in seen:
            dupes.add(case.id)
        seen[normalized] = case.id
    return dupes
