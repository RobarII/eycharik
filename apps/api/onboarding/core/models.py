"""Domain types shared by the pure core, the ports, and the persistence layer.

Every identifier is a distinct ``NewType`` so a run id cannot be passed where a chunk id is
expected. Every value object is frozen: a transition returns a new state instead of mutating one.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import NewType

EmployeeId = NewType("EmployeeId", str)
RunId = NewType("RunId", str)
ChatId = NewType("ChatId", int)
DocId = NewType("DocId", str)
ChunkId = NewType("ChunkId", str)

MAX_MESSAGE_CHARS = 4000


class EventKind(StrEnum):
    EMPLOYEE_CREATED = "employee_created"
    MESSAGE_RECEIVED = "message_received"
    BUTTON_PRESSED = "button_pressed"
    FILE_RECEIVED = "file_received"
    TIMEOUT = "timeout"


class StepKind(StrEnum):
    SEND = "send"
    WAIT = "wait"
    TERMINAL = "terminal"


class Expects(StrEnum):
    MESSAGE = "message"
    BUTTON = "button"
    FILE = "file"


class TimeoutAction(StrEnum):
    REMIND = "remind"
    ESCALATE = "escalate"


class ActionKind(StrEnum):
    SEND = "send"
    ANSWER = "answer"
    ESCALATE = "escalate"
    COMPLETE = "complete"
    IGNORE = "ignore"


class Outcome(StrEnum):
    COMPLETED = "completed"
    ESCALATED = "escalated"


class RefusalReason(StrEnum):
    NO_SOURCES = "no_sources"
    LOW_CONFIDENCE = "low_confidence"
    RESTRICTED = "restricted"
    OUT_OF_SCOPE = "out_of_scope"


class EscalationReason(StrEnum):
    NO_SOURCES = "no_sources"
    LOW_CONFIDENCE = "low_confidence"
    RESTRICTED = "restricted"
    OUT_OF_SCOPE = "out_of_scope"
    TIMEOUT = "timeout"
    MANUAL = "manual"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class Button:
    id: str
    text: str


Keyboard = tuple[tuple[Button, ...], ...]


@dataclass(frozen=True, slots=True)
class Timeout:
    after: timedelta
    action: TimeoutAction
    next_step: str | None = None


@dataclass(frozen=True, slots=True)
class Step:
    id: str
    kind: StepKind
    message: str | None = None
    keyboard: Keyboard = ()
    expects: Expects | None = None
    routes: Mapping[str, str] = field(default_factory=dict)
    next_step: str | None = None
    timeout: Timeout | None = None
    escalate_to: str | None = None
    outcome: Outcome | None = None


@dataclass(frozen=True, slots=True)
class Scenario:
    id: str
    version: int
    title: str
    start: str
    steps: Mapping[str, Step]

    def step(self, step_id: str) -> Step:
        try:
            return self.steps[step_id]
        except KeyError:
            raise ScenarioError(f"step {step_id!r} is not part of scenario {self.id!r}") from None


class ScenarioError(ValueError):
    """A scenario document violates the contract."""


@dataclass(frozen=True, slots=True)
class EmployeeProfile:
    employee_id: EmployeeId
    name: str
    role: str
    department: str
    started_at: date
    audience: tuple[str, ...]
    recruiter_id: str | None = None

    def onboarding_day(self, on_date: date) -> int:
        return max(1, (on_date - self.started_at).days + 1)


@dataclass(frozen=True, slots=True)
class Event:
    kind: EventKind
    at: datetime
    text: str | None = None
    button_id: str | None = None
    file_id: str | None = None
    employee_id: EmployeeId | None = None


@dataclass(frozen=True, slots=True)
class StepState:
    run_id: RunId
    employee_id: EmployeeId
    scenario_id: str
    scenario_version: int
    step_id: str
    entered_at: datetime
    completed_steps: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Action:
    kind: ActionKind
    text: str | None = None
    keyboard: Keyboard = ()
    reason: EscalationReason | None = None
    outcome: Outcome | None = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class KeepReminder:
    """Leave the persisted reminder as it is."""


@dataclass(frozen=True, slots=True)
class ScheduleReminder:
    due_at: datetime
    step_id: str
    action: TimeoutAction


@dataclass(frozen=True, slots=True)
class CancelReminder:
    """Drop the persisted reminder; the run no longer waits for this step."""


ReminderPlan = KeepReminder | ScheduleReminder | CancelReminder


@dataclass(frozen=True, slots=True)
class Transition:
    state: StepState
    actions: tuple[Action, ...]
    reminder: ReminderPlan


@dataclass(frozen=True, slots=True)
class Document:
    id: DocId
    title: str
    text: str
    audience: tuple[str, ...]
    valid_from: date
    valid_to: date | None = None
    owner: str = "unknown"


@dataclass(frozen=True, slots=True)
class Chunk:
    id: ChunkId
    doc_id: DocId
    index: int
    text: str


@dataclass(frozen=True, slots=True)
class AnswerDraft:
    answer: str
    citations: tuple[ChunkId, ...]
    confidence: float
    escalate: bool
    reason: str


@dataclass(frozen=True, slots=True)
class Verdict:
    accepted: bool
    reason: str
    answer: str
    citations: tuple[ChunkId, ...]


@dataclass(frozen=True, slots=True)
class ScoredChunk:
    chunk: Chunk
    score: float
