"""Job dispatch.

Payloads are validated here, not in the handlers: a malformed job must fail loudly and be retried
or parked, never half-applied.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from onboarding.app.worker.service import OnboardingService
from onboarding.core.models import ChatId, EmployeeId, Event, EventKind
from onboarding.ports import AuditLog, Clock, JobSink


class JobPayloadError(ValueError):
    """The stored payload does not match the job kind."""


class JobRunner:
    def __init__(
        self,
        *,
        queue: JobSink,
        service: OnboardingService,
        clock: Clock,
        audit: AuditLog,
    ) -> None:
        self._queue = queue
        self._service = service
        self._clock = clock
        self._audit = audit

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
        employee_id = EmployeeId(_text(payload, "employee_id"))
        chat_id = ChatId(_integer(payload, "chat_id"))
        if kind == "start":
            await self._service.start(employee_id, chat_id)
            return
        if kind == "message":
            event = _event(payload.get("event"))
        elif kind == "timeout":
            event = Event(kind=EventKind.TIMEOUT, at=self._clock.now())
        else:
            raise JobPayloadError(f"unknown job kind {kind!r}")
        await self._service.handle(employee_id, chat_id, event)


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
    return Event(
        kind=kind,
        at=at,
        text=text if isinstance(text, str) and text else None,
        button_id=button_id if isinstance(button_id, str) and button_id else None,
    )
