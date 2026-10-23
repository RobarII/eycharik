"""Response models. The wire format is pinned by ``docs/contracts/admin-api.md``."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


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
    status: str


class AuditEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    at: datetime
    fields: dict[str, object]


class Question(BaseModel):
    model_config = ConfigDict(frozen=True)

    employee_id: str
    employee_name: str
    text: str
    answered: bool
    reason: str
    citations: list[str]
    asked_at: datetime


class RunList(BaseModel):
    items: list[RunSummary]


class RunDetail(RunSummary):
    step_message: str | None
    scenario: str
    scenario_version: int
    events: list[AuditEvent]
    questions: list[Question]


class QuestionList(BaseModel):
    items: list[Question]


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
