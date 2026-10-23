"""Response models. The wire format is pinned by ``docs/contracts/admin-api.md``."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from onboarding.core.models import Channel


class SessionRequest(BaseModel):
    """The one place a raw token travels in a body instead of a header."""

    token: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class AdminScope(BaseModel):
    """The rows the caller may see. ``None`` means "not narrowed by this dimension"."""

    model_config = ConfigDict(frozen=True)

    recruiter_id: str | None
    department: str | None


class AdminIdentity(BaseModel):
    """Who the caller is and what the cabinet may offer them."""

    model_config = ConfigDict(frozen=True)

    role: str
    subject: str
    scope: AdminScope
    capabilities: list[str]
    expires_at: datetime | None


class RunSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    employee_id: str
    name: str
    role: str
    department: str
    step_id: str
    step_title: str | None
    step_number: int
    steps_total: int
    entered_at: datetime
    updated_at: datetime
    status: str


class AuditEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    at: datetime
    fields: dict[str, object]


class Question(BaseModel):
    model_config = ConfigDict(frozen=True)

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
    assignee: str | None = None


class AssignQuestion(BaseModel):
    """`null` clears the owner; a name must be an admin the server can authenticate."""

    assignee: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None


class AssignedQuestion(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    employee_id: str
    assignee: str | None


class ResolveQuestion(BaseModel):
    text: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
    ]


class ResolvedQuestion(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    employee_id: str
    answered: bool
    resolved_at: datetime
    resolved_by: str


class LinkIdentity(BaseModel):
    """HR links one messenger account to an employee: without a link there is no run (ADR 0019)."""

    model_config = ConfigDict(frozen=True)

    channel: Channel
    external_id: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)
    ]
    employee_id: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)
    ]


class OffboardedEmployee(BaseModel):
    model_config = ConfigDict(frozen=True)

    employee_id: str
    questions_deleted: int
    messages_deleted: int
    runs_closed: int
    audit_redacted: int


class RunList(BaseModel):
    """One page of runs. `next_cursor` is null on the last page; `total` counts the whole scope."""

    items: list[RunSummary]
    next_cursor: str | None = None
    total: int


class RunDetail(RunSummary):
    step_message: str | None
    scenario: str
    scenario_version: int
    tone: str
    events: list[AuditEvent]
    questions: list[Question]


class QuestionList(BaseModel):
    items: list[Question]
    next_cursor: str | None = None
    total: int


class TagCount(BaseModel):
    model_config = ConfigDict(frozen=True)

    tag: str
    count: int


class AnalyticsOverview(BaseModel):
    model_config = ConfigDict(frozen=True)

    active_runs: int
    completed_runs: int
    high_risk: int
    medium_risk: int
    unanswered_questions: int
    resolved_questions: int
    top_tags: list[TagCount]
    since: datetime


class DigestItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    employee_id: str
    employee_name: str
    department: str
    run_id: str
    step_id: str
    step_title: str
    level: str
    reasons: list[str]
    tags: list[str]
    quote: str | None
    at: datetime


class DigestList(BaseModel):
    items: list[DigestItem]
    since: datetime


class KnowledgeDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    type: str
    audience: list[str]
    owner: str
    valid_from: date | None
    valid_to: date | None
    updated_at: datetime


class KnowledgeList(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[KnowledgeDocument]


class KnowledgeUpload(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str = Field(min_length=20, max_length=200_000)


class KnowledgeUploaded(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    chunks: int


class KnowledgeFileQueued(BaseModel):
    """A file accepted for extraction. It is not in the corpus yet, and the cabinet says so."""

    model_config = ConfigDict(frozen=True)

    content_hash: str
    status: str


class KnowledgeExtraction(BaseModel):
    """What happened to one uploaded file under the active extraction profile."""

    model_config = ConfigDict(frozen=True)

    content_hash: str
    status: str
    reason: str | None = None
    engine: str
    route: str
    pages: int
    min_confidence: float
    document_id: str | None = None
