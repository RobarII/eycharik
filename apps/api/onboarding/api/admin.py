"""Recruiter cabinet API.

Recruiters see their own employees. HR sees everyone. A run outside the caller's scope answers 404,
the same as a run that does not exist: the existence of other employees is not the caller's
business.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from onboarding.api.auth import AdminPrincipal, current_admin
from onboarding.api.schemas import (
    AuditEvent,
    Question,
    QuestionList,
    RunDetail,
    RunList,
    RunSummary,
)
from onboarding.app.admin.queries import AdminQueries, QuestionRecord, RunRecord
from onboarding.app.scenarios import ScenarioCatalog, ScenarioCatalogError

router = APIRouter(prefix="/admin/api", tags=["admin"])

Admin = Annotated[AdminPrincipal, Depends(current_admin)]


def _queries(request: Request) -> AdminQueries:
    return AdminQueries(request.app.state.container.database)


def _scope(principal: AdminPrincipal) -> str | None:
    return None if principal.is_hr else principal.subject


@router.get("/runs", response_model=RunList)
async def list_runs(
    request: Request,
    principal: Admin,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> RunList:
    catalog = request.app.state.container.catalog
    records = await _queries(request).runs(recruiter_id=_scope(principal), limit=limit)
    return RunList(items=[_summary(record, catalog) for record in records])


@router.get("/runs/{run_id}", response_model=RunDetail)
async def run_detail(request: Request, principal: Admin, run_id: str) -> RunDetail:
    queries = _queries(request)
    record = await queries.run(run_id, recruiter_id=_scope(principal))
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "run not found")

    catalog: ScenarioCatalog = request.app.state.container.catalog
    summary = _summary(record, catalog)
    try:
        step = catalog.get(record.scenario_id, record.scenario_version).step(record.step_id)
    except ScenarioCatalogError:
        step_message = None
    else:
        step_message = step.message

    events = await queries.events(record.employee_id)
    questions = await queries.questions(
        recruiter_id=_scope(principal), answered=None, limit=20
    )
    return RunDetail(
        **summary.model_dump(),
        step_message=step_message,
        scenario=record.scenario_id,
        scenario_version=record.scenario_version,
        events=[
            AuditEvent(name=event.name, at=event.at, fields=event.fields) for event in events
        ],
        questions=[_question(question) for question in questions],
    )


@router.get("/questions", response_model=QuestionList)
async def list_questions(
    request: Request,
    principal: Admin,
    status: Annotated[Literal["unanswered", "answered", "all"], Query()] = "unanswered",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> QuestionList:
    answered = {"unanswered": False, "answered": True, "all": None}[status]
    records = await _queries(request).questions(
        recruiter_id=_scope(principal), answered=answered, limit=limit
    )
    return QuestionList(items=[_question(record) for record in records])


def _summary(record: RunRecord, catalog: ScenarioCatalog) -> RunSummary:
    try:
        scenario = catalog.get(record.scenario_id, record.scenario_version)
    except ScenarioCatalogError:
        number, total = 0, 0
    else:
        ordered = list(scenario.steps)
        number = ordered.index(record.step_id) + 1 if record.step_id in ordered else 0
        total = len(ordered)
    return RunSummary(
        run_id=record.run_id,
        employee_id=record.employee_id,
        name=record.name,
        role=record.role,
        department=record.department,
        step_id=record.step_id,
        step_number=number,
        steps_total=total,
        entered_at=record.entered_at,
        status="active" if record.active else "completed",
    )


def _question(record: QuestionRecord) -> Question:
    return Question(
        text=record.text,
        answered=record.answered,
        reason=record.reason,
        citations=record.citations,
        asked_at=record.asked_at,
    )
