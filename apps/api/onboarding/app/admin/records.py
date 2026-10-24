"""Read-side data shapes.

They are plain dataclasses so a route can describe a response without importing SQLAlchemy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class RunRecord:
    run_id: str
    employee_id: str
    name: str
    role: str
    department: str
    scenario_id: str
    scenario_version: int
    tone: str
    step_id: str
    entered_at: datetime
    updated_at: datetime
    active: bool


@dataclass(frozen=True, slots=True)
class EventRecord:
    name: str
    at: datetime
    fields: dict[str, object]


@dataclass(frozen=True, slots=True)
class QuestionRecord:
    id: int
    employee_id: str
    employee_name: str
    text: str
    answered: bool
    reason: str
    citations: list[str]
    asked_at: datetime
    resolved_at: datetime | None
    resolved_by: str | None
    assignee: str | None


@dataclass(frozen=True, slots=True)
class OverviewRecord:
    active_runs: int
    completed_runs: int
    high_risk: int
    medium_risk: int
    unanswered_questions: int
    resolved_questions: int
    top_tags: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class DigestRecord:
    employee_id: str
    employee_name: str
    department: str
    run_id: str
    step_id: str
    step_title: str
    level: str
    reasons: tuple[str, ...]
    tags: tuple[str, ...]
    quote: str | None
    at: datetime


@dataclass(frozen=True, slots=True)
class KnowledgeRecord:
    id: str
    title: str
    type: str
    audience: tuple[str, ...]
    owner: str
    valid_from: date | None
    valid_to: date | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class RunCursor:
    """The sort key of the last row on a page: ``(updated_at, id)``, newest first."""

    at: datetime
    run_id: str


@dataclass(frozen=True, slots=True)
class QuestionCursor:
    """The sort key of the last row on a page: unanswered first, then newest asked."""

    answered: bool
    asked_at: datetime
    id: int
