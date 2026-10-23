"""Recruiter cabinet API.

Recruiters see their own employees. HR sees everyone. A run outside the caller's scope answers 404,
the same as a run that does not exist: the existence of other employees is not the caller's
business.
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)

from onboarding.api.auth import (
    SESSION_COOKIE,
    SESSION_PATH,
    SESSION_TTL,
    AdminPrincipal,
    authenticate,
    current_admin,
)
from onboarding.api.schemas import (
    AdminIdentity,
    AdminScope,
    AnalyticsOverview,
    AuditEvent,
    DigestItem,
    DigestList,
    KnowledgeDocument,
    KnowledgeExtraction,
    KnowledgeFileQueued,
    KnowledgeList,
    KnowledgeUpload,
    KnowledgeUploaded,
    OffboardedEmployee,
    Question,
    QuestionList,
    ResolvedQuestion,
    ResolveQuestion,
    RunDetail,
    RunList,
    RunSummary,
    SessionRequest,
    TagCount,
)
from onboarding.app.admin.actions import (
    EmployeeNotFoundError,
    EmployeeOffboarder,
    QuestionAlreadyResolvedError,
    QuestionNotFoundError,
    QuestionResolver,
)
from onboarding.app.admin.queries import AdminQueries, QuestionRecord, RunRecord
from onboarding.app.db.kb import PostgresKnowledgeWriter
from onboarding.app.db.queue import JobQueue
from onboarding.app.knowledge.extract.media import SUPPORTED, media_type_for
from onboarding.app.knowledge.ingest import (
    CorpusError,
    load_schema,
    validate_frontmatter,
)
from onboarding.app.knowledge.pipeline import ingest_document
from onboarding.app.scenarios import ScenarioCatalog, ScenarioCatalogError
from onboarding.app.worker.jobs import EXTRACT_DOCUMENT

router = APIRouter(prefix="/admin/api", tags=["admin"])

log = logging.getLogger("onboarding.api.admin")

Admin = Annotated[AdminPrincipal, Depends(current_admin)]


def _queries(request: Request) -> AdminQueries:
    return AdminQueries(request.app.state.container.database)


def _scope(principal: AdminPrincipal) -> str | None:
    """The recruiter id predicate; HR is unscoped and a manager is scoped by department."""
    return principal.subject if principal.role == "recruiter" else None


def _department(principal: AdminPrincipal) -> str | None:
    return principal.subject if principal.is_manager else None


@router.get("/me", response_model=AdminIdentity)
async def whoami(principal: Admin) -> AdminIdentity:
    """Who the caller is and what the cabinet may offer them.

    The cabinet renders buttons from ``capabilities`` instead of guessing from an opaque token, and
    a capability the server does not grant never becomes a button that fails with 403.
    """
    return AdminIdentity(
        role=principal.role,
        subject=principal.subject,
        scope=AdminScope(
            recruiter_id=_scope(principal),
            department=_department(principal),
        ),
        capabilities=list(principal.capabilities),
        expires_at=principal.expires_at,
    )


@router.post("/session", status_code=status.HTTP_204_NO_CONTENT)
async def open_session(request: Request, body: SessionRequest, response: Response) -> None:
    """Trade a token for an HttpOnly session cookie.

    The token is never stored by the page: it arrives once in a JSON body and leaves as a cookie the
    script cannot read. A wrong token is throttled here exactly like a wrong bearer header.
    """
    principal = await authenticate(request, body.token)
    container = request.app.state.container
    response.set_cookie(
        SESSION_COOKIE,
        body.token,
        max_age=int(SESSION_TTL.total_seconds()),
        path=SESSION_PATH,
        httponly=True,
        samesite="strict",
        secure=container.settings.environment != "local",
    )
    log.info(
        json.dumps(
            {"event": "admin_session_opened", "role": principal.role, "subject": principal.subject},
            ensure_ascii=False,
        )
    )


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
async def close_session(request: Request, response: Response) -> None:
    """Clear the cookie.

    Open by design: signing out must work even for a token that just expired.
    """
    response.delete_cookie(SESSION_COOKIE, path=SESSION_PATH)
    log.info(json.dumps({"event": "admin_session_closed"}, ensure_ascii=False))


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


@router.post(
    "/questions/{question_id}/resolve",
    response_model=ResolvedQuestion,
)
async def resolve_question(
    request: Request,
    principal: Admin,
    question_id: int,
    body: ResolveQuestion,
) -> ResolvedQuestion:
    """Close one escalated question and queue the recruiter's reply in the outbox."""
    container = request.app.state.container
    resolver = QuestionResolver(container.database, container.clock)
    try:
        resolution = await resolver.resolve(
            question_id,
            text=body.text,
            actor=principal.subject,
            recruiter_id=_scope(principal),
            department=_department(principal),
        )
    except QuestionNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "question not found") from None
    except QuestionAlreadyResolvedError:
        raise HTTPException(status.HTTP_409_CONFLICT, "question already resolved") from None
    return ResolvedQuestion(
        id=resolution.question_id,
        employee_id=resolution.employee_id,
        answered=True,
        resolved_at=resolution.resolved_at,
        resolved_by=resolution.resolved_by,
    )


@router.delete(
    "/employees/{employee_id}",
    response_model=OffboardedEmployee,
)
async def offboard_employee(
    request: Request,
    principal: Admin,
    employee_id: str,
) -> OffboardedEmployee:
    """HR offboards an employee: the run stops and the transcript is deleted immediately."""
    if not principal.is_hr:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="only hr_admin may offboard an employee",
        )
    container = request.app.state.container
    offboarder = EmployeeOffboarder(container.database, container.clock)
    try:
        result = await offboarder.offboard(employee_id, actor=principal.subject)
    except EmployeeNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "employee not found") from None
    return OffboardedEmployee(
        employee_id=result.employee_id,
        questions_deleted=result.questions_deleted,
        messages_deleted=result.messages_deleted,
        runs_closed=result.runs_closed,
        audit_redacted=result.audit_redacted,
    )


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
        id=record.id,
        employee_id=record.employee_id,
        employee_name=record.employee_name,
        text=record.text,
        answered=record.answered,
        reason=record.reason,
        citations=record.citations,
        asked_at=record.asked_at,
        resolved_at=record.resolved_at,
        resolved_by=record.resolved_by,
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
        resolved_questions=record.resolved_questions,
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


@router.post(
    "/knowledge/files",
    response_model=KnowledgeFileQueued,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_knowledge_file(
    request: Request,
    principal: Admin,
    file: Annotated[UploadFile, File()],
    metadata: Annotated[str, Form()],
) -> KnowledgeFileQueued:
    """Accept a PDF or a deck, store it by hash, and queue extraction.

    The request does no heavy work: recognition takes seconds per page, so it happens in the worker
    and the cabinet polls ``/knowledge/files/{content_hash}``. The metadata is validated here,
    against the same contract a committed document obeys, so a bad upload fails fast.
    """
    if not principal.is_hr:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="only hr_admin may change the knowledge base",
        )
    container = request.app.state.container
    limit = container.settings.extraction_max_upload_bytes
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"upload exceeds {limit} bytes",
        )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="empty upload"
        )

    media_type = media_type_for(file.filename or "", file.content_type)
    if media_type not in SUPPORTED:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="supported formats: PDF, PPTX",
        )

    frontmatter = _file_metadata(metadata, container.settings.contracts_dir)
    blob_id = await container.blobs.put(
        content, filename=file.filename or "upload", media_type=media_type
    )
    async with container.database.session() as session:
        await JobQueue.enqueue(
            session,
            EXTRACT_DOCUMENT,
            {
                "blob_id": blob_id,
                "filename": file.filename or "upload",
                "media_type": media_type,
                "metadata": frontmatter,
            },
        )
    await container.audit.record(
        "knowledge_file_queued",
        blob=blob_id,
        media_type=media_type,
        by=principal.subject,
    )
    return KnowledgeFileQueued(content_hash=blob_id, status="queued")


@router.get("/knowledge/files/{content_hash}", response_model=KnowledgeExtraction)
async def extraction_status(
    request: Request, principal: Admin, content_hash: str
) -> KnowledgeExtraction:
    record = await request.app.state.container.extraction_cache.load_latest(content_hash)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="no extraction for this file"
        )
    return KnowledgeExtraction(
        content_hash=record.content_hash,
        status=record.status,
        reason=record.reason,
        engine=record.engine,
        route=record.route,
        pages=record.pages,
        min_confidence=record.min_confidence,
        document_id=record.document_id,
    )


def _file_metadata(raw: str, contracts_dir: Path) -> dict[str, Any]:
    """Parse the form's JSON metadata and validate it against ``doc.schema.json``."""
    try:
        parsed: Any = json.loads(raw)
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"metadata is not valid JSON: {error}",
        ) from None
    try:
        return validate_frontmatter(
            parsed, load_schema(contracts_dir / "doc.schema.json"), source="upload"
        )
    except CorpusError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from None
