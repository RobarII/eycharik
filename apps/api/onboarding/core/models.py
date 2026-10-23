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

# The domain cap for one message body. A channel profile may lower it; nothing may raise it, so a
# scenario step stays renderable on the strictest supported messenger.
MAX_MESSAGE_CHARS = 4000
MAX_TITLE_CHARS = 80


class Channel(StrEnum):
    """Where a conversation happens. A value, not a client: adapters live in ``app/channels``."""

    MAX = "max"
    TELEGRAM = "telegram"
    VK = "vk"


@dataclass(frozen=True, slots=True)
class Address:
    """One conversation on one messenger. The run, the outbox and the question log store this."""

    channel: Channel
    chat_id: ChatId

    def key(self) -> str:
        return f"{self.channel}:{self.chat_id}"


class EventKind(StrEnum):
    EMPLOYEE_CREATED = "employee_created"
    MESSAGE_RECEIVED = "message_received"
    BUTTON_PRESSED = "button_pressed"
    FILE_RECEIVED = "file_received"
    TIMEOUT = "timeout"


class StepKind(StrEnum):
    SEND = "send"
    WAIT = "wait"
    SURVEY = "survey"
    TERMINAL = "terminal"


class Tone(StrEnum):
    FORMAL = "formal"
    INFORMAL = "informal"


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
    title: str | None = None
    message: str | None = None
    keyboard: Keyboard = ()
    expects: Expects | None = None
    routes: Mapping[str, str] = field(default_factory=dict)
    next_step: str | None = None
    timeout: Timeout | None = None
    questions: tuple[Question, ...] = ()
    escalate_to: str | None = None
    outcome: Outcome | None = None
    informal_message: str | None = None
    tone_routes: Mapping[str, Tone] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Scenario:
    id: str
    version: int
    title: str
    start: str
    steps: Mapping[str, Step]
    segments: tuple[str, ...] = ()

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
    scenario_id: str = "onboarding_default"

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
    answers: tuple[SurveyAnswer, ...] = ()
    question_index: int = 0
    pending_reason: str | None = None
    tone: Tone = Tone.FORMAL


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
    # Generated once at ingest by a contextual-retrieval pass (ADR 0016). Empty means the chunk is
    # embedded and indexed on its own text, which is the default behaviour.
    context: str = ""

    @property
    def embedding_text(self) -> str:
        """What the embedder and the lexical index see; ``text`` stays the quotable source."""
        if not self.context:
            return self.text
        return f"{self.context}\n\n{self.text}"


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


class Sentiment(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    UNKNOWN = "unknown"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SignalTag(StrEnum):
    ACCESS = "access"
    MANAGER = "manager"
    COLLEAGUES = "colleagues"
    WORKLOAD = "workload"
    CLARITY = "clarity"
    HR = "hr"
    IT = "it"
    INTEGRATION = "integration"
    OTHER = "other"


class QuestionKind(StrEnum):
    CHOICE = "choice"
    SCALE = "scale"
    OPEN = "open"


MAX_SCALE = 10
MIN_SCALE = 1
MAX_REASON_CHARS = 1000


@dataclass(frozen=True, slots=True)
class Question:
    id: str
    prompt: str
    kind: QuestionKind
    options: tuple[Button, ...] = ()
    low_threshold: int | None = None
    reason_prompt: str | None = None

    def validate(self) -> None:
        if self.kind is QuestionKind.CHOICE and not self.options:
            raise SurveyError(f"question {self.id!r}: a choice question needs options")
        if self.kind is not QuestionKind.CHOICE and self.options:
            raise SurveyError(f"question {self.id!r}: only a choice question has options")
        if self.kind is QuestionKind.SCALE:
            if self.low_threshold is None:
                raise SurveyError(f"question {self.id!r}: a scale question needs low_threshold")
            if not MIN_SCALE < self.low_threshold <= MAX_SCALE:
                raise SurveyError(
                    f"question {self.id!r}: low_threshold must be between {MIN_SCALE + 1} "
                    f"and {MAX_SCALE}"
                )


@dataclass(frozen=True, slots=True)
class SurveyAnswer:
    question_id: str
    text: str | None = None
    option_id: str | None = None
    score: int | None = None


@dataclass(frozen=True, slots=True)
class RiskSignal:
    source: str
    sentiment: Sentiment
    tags: tuple[SignalTag, ...]
    confidence: float
    text: str | None = None
    score: int | None = None
    low_threshold: int | None = None


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    level: RiskLevel
    tags: tuple[SignalTag, ...]
    escalate_to: str | None
    reasons: tuple[str, ...]
    score: int


class SurveyError(ValueError):
    """A survey answer or definition violates the contract."""


# --- Document extraction ---------------------------------------------------
#
# Everything below describes what came out of a file, never how it was read. An engine name is a
# string carried for the audit trail; no code branches on it.


class ExtractionRoute(StrEnum):
    """How a document reached the corpus. ``REJECTED`` means the file never became text."""

    NATIVE_TEXT = "native_text"
    OCR = "ocr"
    REJECTED = "rejected"


class RejectionReason(StrEnum):
    """Why a file produced no usable text. One enum for the reader, the gate, and acceptance."""

    UNSUPPORTED = "unsupported"
    ENCRYPTED = "encrypted"
    NO_PAGES = "no_pages"
    TOO_MANY_PAGES = "too_many_pages"
    UNREADABLE = "unreadable"
    LOW_DPI = "low_dpi"
    BLURRY = "blurry"
    EMPTY = "empty"
    LOW_CONFIDENCE = "low_confidence"
    TOO_SHORT = "too_short"


@dataclass(frozen=True, slots=True)
class ImageMetrics:
    """What the quality gate can measure about one raster.

    A metric the reader cannot produce is ``None`` and its check is skipped. Nothing is invented to
    fill the field: an unmeasured page is not a sharp one.
    """

    dpi: int | None = None
    edge_energy: float | None = None
    width: int = 0
    height: int = 0


@dataclass(frozen=True, slots=True)
class QualityPolicy:
    """Thresholds for the pre-recognition gate. ``None`` disables one check.

    The defaults are provisional and live in the extraction profile; calibrate them on the golden
    set before claiming a quality number.
    """

    min_dpi: int | None = 200
    min_edge_energy: float | None = None


@dataclass(frozen=True, slots=True)
class QualityVerdict:
    ok: bool
    reasons: tuple[RejectionReason, ...] = ()

    @property
    def reason(self) -> RejectionReason | None:
        return self.reasons[0] if self.reasons else None


@dataclass(frozen=True, slots=True)
class DocumentSniff:
    """Cheap facts about a file, before any expensive step."""

    page_count: int
    pages: tuple[str, ...] = ()
    metrics: ImageMetrics = field(default_factory=ImageMetrics)
    encrypted: bool = False

    @property
    def text_chars(self) -> int:
        return sum(len(page.strip()) for page in self.pages)

    @property
    def text(self) -> str:
        return "\n\n".join(page for page in self.pages if page.strip())


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    index: int
    text: str
    confidence: float = 1.0
    engine: str = ""
    route: ExtractionRoute = ExtractionRoute.NATIVE_TEXT


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    """The whole outcome of reading one file, including a refusal."""

    pages: tuple[ExtractedPage, ...]
    engine: str
    content_hash: str
    route: ExtractionRoute
    profile: str = ""
    profile_hash: str = ""
    refusal: RejectionReason | None = None


@dataclass(frozen=True, slots=True)
class AcceptancePolicy:
    min_confidence: float = 0.72
    min_chars: int = 40


@dataclass(frozen=True, slots=True)
class Accepted:
    text: str
    pages: int
    min_confidence: float


@dataclass(frozen=True, slots=True)
class Rejected:
    reason: RejectionReason
    page: int | None = None
    detail: str = ""


Acceptance = Accepted | Rejected
