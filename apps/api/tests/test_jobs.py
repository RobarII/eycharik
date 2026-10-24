from __future__ import annotations

from datetime import UTC, datetime

import pytest

from onboarding.app.audit import NullAudit
from onboarding.app.clock import FrozenClock
from onboarding.app.worker.jobs import JobPayloadError, JobRunner
from onboarding.ports import ClaimedJob

NOW = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)


class StubService:
    def __init__(self) -> None:
        self.started: list[tuple[str, str, int]] = []
        self.handled: list[tuple[str, str, int, str]] = []

    async def start(self, employee_id: object, address: object) -> None:
        self.started.append(_address(employee_id, address))

    async def handle(self, employee_id: object, address: object, event: object) -> None:
        owner, channel, chat_id = _address(employee_id, address)
        self.handled.append((owner, channel, chat_id, event.kind.value))  # type: ignore[attr-defined]


def _address(employee_id: object, address: object) -> tuple[str, str, int]:
    channel = address.channel
    chat_id = address.chat_id
    return (str(employee_id), str(channel), int(chat_id))


class StubExtractor:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    async def run(self, payload: object) -> None:
        self.payloads.append(dict(payload))  # type: ignore[arg-type]


class StubIndexer:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    async def run(self, payload: object) -> None:
        self.payloads.append(dict(payload))  # type: ignore[arg-type]


class StubFiles:
    def __init__(self) -> None:
        self.saved: list[tuple[str, str, int, tuple[str, ...]]] = []

    async def save(self, employee_id: object, address: object, files: object) -> list[str]:
        owner, channel, chat_id = _address(employee_id, address)
        tokens = tuple(file.token for file in files)  # type: ignore[attr-defined]
        self.saved.append((owner, channel, chat_id, tokens))
        return []


class RecordingQueue:
    def __init__(self) -> None:
        self.completed: list[int] = []
        self.failed: list[tuple[int, str]] = []

    async def claim(self) -> tuple[ClaimedJob, ...]:
        return ()

    async def complete(self, job: ClaimedJob) -> None:
        self.completed.append(job.id)

    async def fail(self, job: ClaimedJob, error: Exception) -> None:
        self.failed.append((job.id, type(error).__name__))


def build_with_indexer() -> tuple[JobRunner, StubIndexer]:
    indexer = StubIndexer()
    runner = JobRunner(
        queue=RecordingQueue(),  # type: ignore[arg-type]
        service=StubService(),  # type: ignore[arg-type]
        clock=FrozenClock(NOW),
        audit=NullAudit(),
        extractor=StubExtractor(),  # type: ignore[arg-type]
        indexer=indexer,  # type: ignore[arg-type]
        files=StubFiles(),  # type: ignore[arg-type]
    )
    return runner, indexer


def build() -> tuple[JobRunner, StubService, RecordingQueue]:
    runner, service, queue, _ = build_with_extractor()
    return runner, service, queue


def build_with_extractor() -> tuple[JobRunner, StubService, RecordingQueue, StubExtractor]:
    service = StubService()
    queue = RecordingQueue()
    extractor = StubExtractor()
    runner = JobRunner(
        queue=queue,  # type: ignore[arg-type]
        service=service,  # type: ignore[arg-type]
        clock=FrozenClock(NOW),
        audit=NullAudit(),
        extractor=extractor,  # type: ignore[arg-type]
        indexer=StubIndexer(),  # type: ignore[arg-type]
        files=StubFiles(),  # type: ignore[arg-type]
    )
    return runner, service, queue, extractor


async def test_start_job_starts_a_run() -> None:
    runner, service, _ = build()

    await runner._dispatch("start", {"employee_id": "1001", "channel": "max", "chat_id": 42})

    assert service.started == [("1001", "max", 42)]


async def test_message_job_restores_the_event() -> None:
    runner, service, _ = build()

    await runner._dispatch(
        "message",
        {
            "employee_id": "1001",
            "channel": "max",
            "chat_id": 42,
            "event": {
                "kind": "message_received",
                "at": "2026-10-23T09:00:00+00:00",
                "text": "привет",
            },
        },
    )

    assert service.handled == [("1001", "max", 42, "message_received")]


async def test_a_file_job_is_stored_before_the_step_is_applied() -> None:
    service = StubService()
    files = StubFiles()
    runner = JobRunner(
        queue=RecordingQueue(),  # type: ignore[arg-type]
        service=service,  # type: ignore[arg-type]
        clock=FrozenClock(NOW),
        audit=NullAudit(),
        extractor=StubExtractor(),  # type: ignore[arg-type]
        indexer=StubIndexer(),  # type: ignore[arg-type]
        files=files,  # type: ignore[arg-type]
    )

    await runner._dispatch(
        "message",
        {
            "employee_id": "1001",
            "channel": "max",
            "chat_id": 42,
            "event": {"kind": "file_received", "at": "2026-10-23T09:00:00+00:00"},
            "files": [
                {
                    "token": "photo-token-1",
                    "url": "https://cdn.test/1",
                    "filename": "passport.jpg",
                    "media_type": "image/jpeg",
                    "size": 1024,
                }
            ],
        },
    )

    assert files.saved == [("1001", "max", 42, ("photo-token-1",))]
    assert service.handled == [("1001", "max", 42, "file_received")]


async def test_a_malformed_file_list_is_rejected() -> None:
    runner, _, _ = build()

    with pytest.raises(JobPayloadError, match="files must be a list"):
        await runner._dispatch(
            "message",
            {
                "employee_id": "1001",
                "channel": "max",
                "chat_id": 42,
                "event": {"kind": "file_received", "at": "2026-10-23T09:00:00+00:00"},
                "files": "passport.jpg",
            },
        )


async def test_timeout_job_uses_the_job_clock() -> None:
    runner, service, _ = build()

    await runner._dispatch("timeout", {"employee_id": "1001", "channel": "max", "chat_id": 42})

    assert service.handled == [("1001", "max", 42, "timeout")]


async def test_unknown_kind_is_rejected() -> None:
    runner, _, _ = build()

    with pytest.raises(JobPayloadError, match="unknown job kind"):
        await runner._dispatch("teleport", {"employee_id": "1001", "channel": "max", "chat_id": 42})


async def test_missing_employee_is_rejected() -> None:
    runner, _, _ = build()

    with pytest.raises(JobPayloadError, match="employee_id"):
        await runner._dispatch("start", {"channel": "max", "chat_id": 42})


async def test_invalid_timestamp_is_rejected() -> None:
    runner, _, _ = build()

    with pytest.raises(ValueError, match="Invalid isoformat"):
        await runner._dispatch(
            "message",
            {
                "employee_id": "1001",
                "channel": "max",
                "chat_id": 42,
                "event": {"kind": "message_received", "at": "yesterday"},
            },
        )


async def test_extract_job_goes_to_the_extractor_not_the_scenario() -> None:
    runner, service, _, extractor = build_with_extractor()
    payload = {"blob_id": "abc", "filename": "a.pdf", "media_type": "application/pdf"}

    await runner._dispatch("extract_document", payload)

    assert extractor.payloads == [payload]
    assert service.handled == []
    assert service.started == []


async def test_index_job_reaches_the_indexer() -> None:
    runner, indexer = build_with_indexer()

    await runner._dispatch("index_document", {"blob_id": "abc"})

    assert indexer.payloads == [{"blob_id": "abc"}]
