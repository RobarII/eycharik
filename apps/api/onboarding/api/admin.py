"""Recruiter cabinet API.

Recruiters see their own employees. HR sees everyone. A run outside the caller's scope answers 404,
the same as a run that does not exist: the existence of other employees is not the caller's
business.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from onboarding.api.auth import AdminPrincipal, current_admin
from onboarding.api.schemas import (
    AnalyticsOverview,
    AuditEvent,
    DigestItem,
    DigestList,
    KnowledgeDocument,
    KnowledgeList,
    KnowledgeUpload,
    KnowledgeUploaded,
    Question,
    QuestionList,
    RunDetail,
    RunList,
    RunSummary,
    TagCount,
)
from onboarding.app.admin.queries import AdminQueries, QuestionRecord, RunRecord
from onboarding.app.db.kb import PostgresKnowledgeWriter
from onboarding.app.knowledge.ingest import CorpusError
from onboarding.app.knowledge.pipeline import ingest_document
from onboarding.app.scenarios import ScenarioCatalog, ScenarioCatalogError

router = APIRouter(prefix="/admin/api", tags=["admin"])

Admin = Annotated[AdminPrincipal, Depends(current_admin)]


def _queries(request: Request) -> AdminQueries:
    return AdminQueries(request.app.state.container.database)


def _scope(principal: AdminPrincipal) -> str | None:
    """The recruiter id predicate; HR is unscoped and a manager is scoped by department."""
    return principal.subject if principal.role == "recruiter" else None


def _department(principal: AdminPrincipal) -> str | None:
    return principal.subject if principal.is_manager else None


@router.get("/runs", response_model=RunList)
async def list_runs(
    request: Request,
    principal: Admin,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> RunList:
    catalog = request.app.state.container.catalog
    records = await _queries(request).runs(
        recruiter_id=_scope(principal), department=_department(principal), limit=limit
    )
    return RunList(items=[_summary(record, catalog) for record in records])


@router.get("/runs/{run_id}", response_model=RunDetail)
async def run_detail(request: Request, principal: Admin, run_id: str) -> RunDetail:
    queries = _queries(request)
    record = await queries.run(
        run_id, recruiter_id=_scope(principal), department=_department(principal)
    )
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
        recruiter_id=_scope(principal),
        department=_department(principal),
        answered=None,
        limit=20,
        employee_id=record.employee_id,
    )
    return RunDetail(
        **summary.model_dump(),
        step_message=step_message,
        scenario=record.scenario_id,
        scenario_version=record.scenario_version,
        tone=record.tone,
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
        recruiter_id=_scope(principal),
        department=_department(principal),
        answered=answered,
        limit=limit,
    )
    return QuestionList(items=[_question(record) for record in records])


def _summary(record: RunRecord, catalog: ScenarioCatalog) -> RunSummary:
    step_title: str | None = None
    try:
        scenario = catalog.get(record.scenario_id, record.scenario_version)
    except ScenarioCatalogError:
        number, total = 0, 0
    else:
        ordered = list(scenario.steps)
        number = ordered.index(record.step_id) + 1 if record.step_id in ordered else 0
        total = len(ordered)
        if record.step_id in ordered:
            step_title = scenario.step(record.step_id).title
    return RunSummary(
        run_id=record.run_id,
        employee_id=record.employee_id,
        name=record.name,
        role=record.role,
        department=record.department,
        step_id=record.step_id,
        step_title=step_title,
        step_number=number,
        steps_total=total,
        entered_at=record.entered_at,
        status="active" if record.active else "completed",
    )


def _question(record: QuestionRecord) -> Question:
    return Question(
        employee_id=record.employee_id,
        employee_name=record.employee_name,
        text=record.text,
        answered=record.answered,
        reason=record.reason,
        citations=record.citations,
        asked_at=record.asked_at,
    )


@router.get("/analytics/overview", response_model=AnalyticsOverview)
async def analytics_overview(request: Request, principal: Admin) -> AnalyticsOverview:
    since = request.app.state.container.clock.now() - timedelta(days=7)
    record = await _queries(request).overview(
        recruiter_id=_scope(principal), department=_department(principal), since=since
    )
    return AnalyticsOverview(
        active_runs=record.active_runs,
        completed_runs=record.completed_runs,
        high_risk=record.high_risk,
        medium_risk=record.medium_risk,
        unanswered_questions=record.unanswered_questions,
        top_tags=[TagCount(tag=tag, count=count) for tag, count in record.top_tags],
        since=since,
    )


@router.get("/digest/weekly", response_model=DigestList)
async def weekly_digest(
    request: Request,
    principal: Admin,
    days: Annotated[int, Query(ge=1, le=31)] = 7,
) -> DigestList:
    since = request.app.state.container.clock.now() - timedelta(days=days)
    records = await _queries(request).digest(
        recruiter_id=_scope(principal), department=_department(principal), since=since
    )
    return DigestList(
        items=[
            DigestItem(
                employee_id=record.employee_id,
                employee_name=record.employee_name,
                department=record.department,
                run_id=record.run_id,
                step_id=record.step_id,
                step_title=record.step_title,
                level=record.level,
                reasons=list(record.reasons),
                tags=list(record.tags),
                quote=record.quote,
                at=record.at,
            )
            for record in records
        ],
        since=since,
    )


@router.get("/knowledge", response_model=KnowledgeList)
async def knowledge_documents(request: Request, principal: Admin) -> KnowledgeList:
    records = await _queries(request).knowledge()
    return KnowledgeList(
        items=[
            KnowledgeDocument(
                id=record.id,
                title=record.title,
                type=record.type,
                audience=list(record.audience),
                owner=record.owner,
                valid_from=record.valid_from,
                valid_to=record.valid_to,
                updated_at=record.updated_at,
            )
            for record in records
        ]
    )


@router.post(
    "/knowledge",
    response_model=KnowledgeUploaded,
    status_code=status.HTTP_201_CREATED,
)
async def upload_knowledge(
    request: Request,
    principal: Admin,
    body: KnowledgeUpload,
) -> KnowledgeUploaded:
    """HR uploads one markdown document with frontmatter; it is indexed in the same request."""
    if not principal.is_hr:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="only hr_admin may change the knowledge base",
        )
    container = request.app.state.container
    try:
        indexed = await ingest_document(
            text=body.text,
            source="upload",
            schema_path=container.settings.contracts_dir / "doc.schema.json",
            writer=PostgresKnowledgeWriter(container.database),
            embedder=container.embedder,
        )
    except CorpusError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from None
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from None
    await container.audit.record(
        "knowledge_ingested",
        document=indexed.id,
        chunks=indexed.chunks,
        by=principal.subject,
    )
    return KnowledgeUploaded(
        id=indexed.id, title=indexed.title, chunks=indexed.chunks
    )
