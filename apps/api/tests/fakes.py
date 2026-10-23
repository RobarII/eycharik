from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from onboarding.core.models import (
    ChatId,
    Chunk,
    ChunkId,
    DocId,
    EmployeeId,
    EmployeeProfile,
    KeepReminder,
    Keyboard,
    ReminderPlan,
    RunId,
    ScoredChunk,
    StepState,
)
from onboarding.ports import (
    Completion,
    CompletionRequest,
    OutboundMessage,
    SearchQuery,
    StoredRun,
)

NOW = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)
EMPLOYEE = EmployeeId("employee-1")


@dataclass
class ScriptedLLM:
    responses: list[str | Exception] = field(default_factory=list)
    requests: list[CompletionRequest] = field(default_factory=list)

    async def complete(self, request: CompletionRequest) -> Completion:
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("no scripted response left")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return Completion(text=response, input_tokens=10, output_tokens=5, model="scripted")


@dataclass
class FakeKnowledgeBase:
    chunks: tuple[ScoredChunk, ...] = ()
    queries: list[SearchQuery] = field(default_factory=list)

    async def search(self, query: SearchQuery) -> tuple[ScoredChunk, ...]:
        self.queries.append(query)
        return self.chunks


@dataclass
class RecordingMessaging:
    sent: list[OutboundMessage] = field(default_factory=list)
    edited: list[tuple[str, str]] = field(default_factory=list)

    async def send(self, message: OutboundMessage) -> str:
        self.sent.append(message)
        return f"mid-{len(self.sent)}"

    async def edit(self, message_id: str, text: str, keyboard: Keyboard = ()) -> None:
        self.edited.append((message_id, text))


@dataclass
class InMemoryRuns:
    runs: dict[RunId, StoredRun] = field(default_factory=dict)

    async def create(self, run: StoredRun) -> None:
        self.runs[run.state.run_id] = run

    async def load(self, run_id: RunId) -> StoredRun | None:
        return self.runs.get(run_id)

    async def save(self, run: StoredRun) -> None:
        self.runs[run.state.run_id] = run

    async def find_active_by_employee(self, employee_id: EmployeeId) -> StoredRun | None:
        for run in self.runs.values():
            if run.state.employee_id == employee_id:
                return run
        return None

    async def list_active(
        self, *, recruiter_id: str | None, limit: int
    ) -> tuple[StoredRun, ...]:
        del recruiter_id
        return tuple(self.runs.values())[:limit]


@dataclass
class StaticDirectory:
    profiles: dict[EmployeeId, EmployeeProfile] = field(default_factory=dict)

    async def profile(self, employee_id: EmployeeId) -> EmployeeProfile | None:
        return self.profiles.get(employee_id)


@dataclass
class RecordingAudit:
    events: list[tuple[str, dict[str, object]]] = field(default_factory=list)

    async def record(self, name: str, **fields: object) -> None:
        self.events.append((name, fields))

    def names(self) -> list[str]:
        return [event for event, _ in self.events]


def profile(
    employee_id: EmployeeId = EMPLOYEE,
    *,
    department: str = "ИТ",
    audience: tuple[str, ...] = ("all", "dept:it"),
) -> EmployeeProfile:
    return EmployeeProfile(
        employee_id=employee_id,
        name="Иван Иванов",
        role="Инженер",
        department=department,
        started_at=date(2026, 10, 20),
        audience=audience,
    )


def scored_chunk(chunk_id: str = "hr/leave-policy#0") -> ScoredChunk:
    doc_id, _, index = chunk_id.partition("#")
    return ScoredChunk(
        chunk=Chunk(
            id=ChunkId(chunk_id),
            doc_id=DocId(doc_id),
            index=int(index or 0),
            text="Ежегодный оплачиваемый отпуск — 28 календарных дней.",
        ),
        score=0.5,
    )


def stored_run(
    *,
    employee_id: EmployeeId = EMPLOYEE,
    step_id: str = "first_day_checklist",
    reminder: ReminderPlan | None = None,
) -> StoredRun:
    state = StepState(
        run_id=RunId("run-1"),
        employee_id=employee_id,
        scenario_id="onboarding_default",
        scenario_version=1,
        step_id=step_id,
        entered_at=NOW,
    )
    return StoredRun(state=state, reminder=reminder or KeepReminder(), chat_id=ChatId(1))
