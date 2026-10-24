"""Audience and validity rules for knowledge retrieval.

The rule exists once. ``predicates`` assembles it as a conjunction of typed conditions, and three
callers read that conjunction instead of restating it:

- the in-memory backend evaluates it with ``evaluate``;
- the SQL backend compiles it to a ``WHERE`` clause in ``app.db.predicates``;
- the ACL matrix grades the corpus against it.

A rule written twice disagrees with itself eventually — the previous version of this module said
``hr_only`` is never inherited from ``all`` while the SQL clause said an array overlap, and the two
parted company on any document whose audience mixed the two. A rule written once cannot.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable
from dataclasses import dataclass
from datetime import date

from .models import Document

HR_ONLY = "hr_only"
EVERYONE = "all"


@dataclass(frozen=True, slots=True)
class Active:
    """Only an active document is retrievable."""


@dataclass(frozen=True, slots=True)
class ValidOn:
    """The edition is in force on this date."""

    on_date: date


@dataclass(frozen=True, slots=True)
class AudienceVisible:
    """The document is shared with everyone, or overlaps one of the viewer's grants."""

    grants: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HrOnlyNotWithheld:
    """``hr_only`` is granted explicitly or not at all; ``all`` never stands in for it."""

    granted: bool


Predicate = Active | ValidOn | AudienceVisible | HrOnlyNotWithheld


@dataclass(frozen=True, slots=True)
class Subject:
    """What a predicate is evaluated against: the document fields the rule is allowed to read."""

    audience: tuple[str, ...]
    valid_from: date | None = None
    valid_to: date | None = None
    status: str = "active"


def audience_predicates(viewer: Collection[str]) -> tuple[Predicate, ...]:
    """The viewer's half of the rule, the only half that does not need a date."""
    grants = tuple(dict.fromkeys(viewer))
    return (AudienceVisible(grants), HrOnlyNotWithheld(HR_ONLY in grants))


def predicates(viewer: Collection[str], on_date: date) -> tuple[Predicate, ...]:
    """The whole retrieval filter for one viewer on one date."""
    return (Active(), ValidOn(on_date), *audience_predicates(viewer))


def evaluate(predicate: Predicate, subject: Subject) -> bool:
    """Interpret one predicate. Exhaustive on purpose: a new kind must not fall through to True."""
    match predicate:
        case Active():
            return subject.status == "active"
        case ValidOn(on_date):
            if subject.valid_from is not None and on_date < subject.valid_from:
                return False
            return subject.valid_to is None or on_date <= subject.valid_to
        case AudienceVisible(grants):
            return EVERYONE in subject.audience or bool(set(subject.audience) & set(grants))
        case HrOnlyNotWithheld(granted):
            return granted or HR_ONLY not in subject.audience


def holds(predicates: Iterable[Predicate], subject: Subject) -> bool:
    """Every predicate in the conjunction, short-circuiting on the first refusal."""
    return all(evaluate(predicate, subject) for predicate in predicates)


def permits(audience: Collection[str], viewer: Collection[str]) -> bool:
    """May a viewer with these scopes retrieve a chunk with this audience?"""
    return holds(audience_predicates(viewer), Subject(audience=tuple(audience)))


def is_valid(document: Document, on_date: date) -> bool:
    return evaluate(
        ValidOn(on_date),
        Subject(
            audience=document.audience,
            valid_from=document.valid_from,
            valid_to=document.valid_to,
        ),
    )


def subject_of(document: Document, *, status: str = "active") -> Subject:
    return Subject(
        audience=tuple(document.audience),
        valid_from=document.valid_from,
        valid_to=document.valid_to,
        status=status,
    )
