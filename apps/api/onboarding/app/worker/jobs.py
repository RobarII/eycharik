"""Job dispatch.

Payloads are validated here, not in the handlers: a malformed job must fail loudly and be retried
or parked, never half-applied.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from onboarding.app.files.intake import InboundFileIntake
from onboarding.app.jobs import EXTRACT_DOCUMENT, INDEX_DOCUMENT, MESSAGE, SEND_STEP, START, TIMEOUT
from onboarding.app.worker.extract import DocumentExtractor
from onboarding.app.worker.index import DocumentIndexer
from onboarding.app.worker.payload import JobPayloadError
from onboarding.app.worker.service import OnboardingService
from onboarding.core.models import Address, Channel, ChatId, EmployeeId, Event, EventKind, RunId
from onboarding.ports import AuditLog, Clock, InboundFile, JobSink


class JobRunner:
    def __init__(
        self,
        *,
        queue: JobSink,
        service: OnboardingService,
        clock: Clock,
        audit: AuditLog,
        extractor: DocumentExtractor,
        indexer: DocumentIndexer,
        files: InboundFileIntake,
    ) -> None:
        self._queue = queue
        self._service = service
        self._clock = clock
        self._audit = audit
        self._extractor = extractor
        self._indexer = indexer
        self._files = files

    async def run_once(self) -> int:
        jobs = await self._queue.claim()
        for job in jobs:
            try:
                await self._dispatch(job.kind, job.payload)
            except Exception as error:  # noqa: BLE001 - one bad job must not stop the loop
                await self._queue.fail(job, error)
                await self._audit.record(
                    "job_failed",
                    job_id=job.id,
                    kind=job.kind,
                    error=type(error).__name__,
                    detail=str(error)[:300],
                )
            else:
                await self._queue.complete(job)
        return len(jobs)

    async def _dispatch(self, kind: str, payload: Mapping[str, object]) -> None:
        if kind == EXTRACT_DOCUMENT:
            await self._extractor.run(payload)
            return
        if kind == INDEX_DOCUMENT:
            await self._indexer.run(payload)
            return
        if kind == SEND_STEP:
            await self._service.resume_scheduled(
                RunId(_text(payload, "run_id")), _text(payload, "step_id")
            )
            return
        employee_id = EmployeeId(_text(payload, "employee_id"))
        address = Address(
            channel=Channel(_text(payload, "channel")),
            chat_id=ChatId(_integer(payload, "chat_id")),
        )
        if kind == START:
            await self._service.start(employee_id, address)
            return
        if kind == MESSAGE:
            event = _event(payload.get("event"))
            attachments = _files(payload.get("files"))
            if attachments:
                # Stored before the step is applied, so a recruiter sees the document even if the
                # reply that follows fails. The webhook already answered 200; this is the slow part.
                await self._files.save(employee_id, address, attachments)
        elif kind == TIMEOUT:
            event = Event(kind=EventKind.TIMEOUT, at=self._clock.now())
        else:
            raise JobPayloadError(f"unknown job kind {kind!r}")
        await self._service.handle(employee_id, address, event)


def _text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise JobPayloadError(f"{key} must be a non-empty string")
    return value


def _integer(payload: Mapping[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise JobPayloadError(f"{key} must be an integer")
    return value


def _files(raw: object) -> tuple[InboundFile, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise JobPayloadError("files must be a list")
    files: list[InboundFile] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise JobPayloadError("each file must be a mapping")
        token = item.get("token")
        if not isinstance(token, str) or not token:
            raise JobPayloadError("file.token must be a non-empty string")
        files.append(
            InboundFile(
                token=token,
                url=_optional_text(item, "url"),
                filename=_optional_text(item, "filename"),
                media_type=_optional_text(item, "media_type"),
                size=_optional_int(item, "size"),
            )
        )
    return tuple(files)


def _optional_text(raw: Mapping[str, object], key: str) -> str | None:
    value = raw.get(key)
    return value if isinstance(value, str) and value else None


def _optional_int(raw: Mapping[str, object], key: str) -> int | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise JobPayloadError(f"file.{key} must be a non-negative integer")
    return value


def _event(raw: object) -> Event:
    if not isinstance(raw, Mapping):
        raise JobPayloadError("event must be a mapping")
    kind_value = raw.get("kind")
    at_value = raw.get("at")
    if not isinstance(kind_value, str):
        raise JobPayloadError("event.kind must be a string")
    try:
        kind = EventKind(kind_value)
    except ValueError:
        raise JobPayloadError(f"unknown event kind {kind_value!r}") from None
    if not isinstance(at_value, str | datetime):
        raise JobPayloadError("event.at must be a timestamp")
    at = datetime.fromisoformat(at_value) if isinstance(at_value, str) else at_value
    text = raw.get("text")
    button_id = raw.get("button_id")
    file_id = raw.get("file_id")
    return Event(
        kind=kind,
        at=at,
        text=text if isinstance(text, str) and text else None,
        button_id=button_id if isinstance(button_id, str) and button_id else None,
        file_id=file_id if isinstance(file_id, str) and file_id else None,
    )
