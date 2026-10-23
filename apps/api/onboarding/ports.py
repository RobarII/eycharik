"""Protocols between the pure core and the outside world.

Implementations live in ``onboarding.app``. The core imports this module only for typing; nothing
here performs I/O.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol, runtime_checkable

from onboarding.core.models import (
    ChatId,
    Chunk,
    DocId,
    EmployeeId,
    EmployeeProfile,
    Keyboard,
    ReminderPlan,
    RunId,
    ScoredChunk,
    StepState,
)


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime:
        """Current time in UTC. The only source of time in the application."""
        ...


@dataclass(frozen=True, slots=True)
class Message:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class CompletionRequest:
    messages: tuple[Message, ...]
    temperature: float = 0.2
    max_tokens: int = 700
    prompt_name: str = "answer"
    prompt_version: int = 1
    response_format: str = "json_object"
    timeout_s: float = 8.0


@dataclass(frozen=True, slots=True)
class Completion:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    latency_ms: int = 0
    cost_rub: float = 0.0


@runtime_checkable
class LLM(Protocol):
    async def complete(self, request: CompletionRequest) -> Completion:
        """One completion. Raises :class:`LLMUnavailableError` when no provider answered."""
        ...


class LLMUnavailableError(RuntimeError):
    """Every configured provider failed or the circuit breaker is open."""


class KnowledgeUnavailableError(RuntimeError):
    """Retrieval could not run: the embedder or the database is down."""


class RunAlreadyActiveError(RuntimeError):
    """An employee already has an active run; the database enforced it."""


@runtime_checkable
class Embedder(Protocol):
    async def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        """One vector per input text, in the same order."""
        ...


@dataclass(frozen=True, slots=True)
class SearchQuery:
    text: str
    audience: tuple[str, ...]
    on_date: date
    limit: int = 30


@runtime_checkable
class KnowledgeBase(Protocol):
    async def search(self, query: SearchQuery) -> tuple[ScoredChunk, ...]:
        """Active, audience-permitted chunks ranked by relevance. No filtering after the fact."""
        ...


@dataclass(frozen=True, slots=True)
class OutboundMessage:
    chat_id: ChatId
    text: str
    keyboard: Keyboard = ()
    reply_to: str | None = None


@runtime_checkable
class Messaging(Protocol):
    async def send(self, message: OutboundMessage) -> str:
        """Send and return the provider message id."""
        ...

    async def edit(self, message_id: str, text: str, keyboard: Keyboard = ()) -> None:
        """Replace the text of a previously sent message."""
        ...


@runtime_checkable
class Directory(Protocol):
    async def profile(self, employee_id: EmployeeId) -> EmployeeProfile | None:
        """Employee facts needed for the assistant context. ``None`` when unknown."""
        ...


@runtime_checkable
class EventDeduper(Protocol):
    async def claim(self, event_id: str) -> bool:
        """True when this delivery is new. Claims atomically; a repeat answers False."""
        ...


@dataclass(frozen=True, slots=True)
class StoredRun:
    state: StepState
    reminder: ReminderPlan
    chat_id: ChatId
    active: bool = True


@runtime_checkable
class RunRepository(Protocol):
    async def create(self, run: StoredRun) -> None: ...

    async def load(self, run_id: RunId) -> StoredRun | None: ...

    async def save(self, run: StoredRun) -> None: ...

    async def find_active_by_employee(self, employee_id: EmployeeId) -> StoredRun | None: ...

    async def list_active(
        self, *, recruiter_id: str | None, limit: int
    ) -> tuple[StoredRun, ...]: ...


@dataclass(frozen=True, slots=True)
class KnowledgeDocumentRecord:
    id: DocId
    title: str
    doc_type: str
    status: str
    audience: tuple[str, ...]
    valid_from: date
    valid_to: date | None
    owner: str
    checksum: str


@runtime_checkable
class KnowledgeWriter(Protocol):
    async def replace_document(
        self,
        record: KnowledgeDocumentRecord,
        chunks: tuple[Chunk, ...],
        embeddings: tuple[tuple[float, ...], ...],
    ) -> None:
        """Replace all chunks of one document atomically."""
        ...


@runtime_checkable
class QuestionLog(Protocol):
    async def record_question(
        self,
        *,
        employee_id: EmployeeId | None,
        chat_id: ChatId,
        text: str,
        answered: bool,
        reason: str,
        citations: Sequence[str],
        latency_ms: int | None,
    ) -> None:
        """Append one asked question. The recruiter dashboard reads this table."""
        ...


@dataclass(frozen=True, slots=True)
class ClaimedJob:
    id: int
    kind: str
    payload: dict[str, object]
    attempts: int


@runtime_checkable
class JobSink(Protocol):
    async def claim(self) -> tuple[ClaimedJob, ...]: ...

    async def complete(self, job: ClaimedJob) -> None: ...

    async def fail(self, job: ClaimedJob, error: Exception) -> None: ...


@runtime_checkable
class AuditLog(Protocol):
    async def record(self, name: str, **fields: object) -> None:
        """Append-only record. Fields must not contain secrets or raw personal data."""
        ...
