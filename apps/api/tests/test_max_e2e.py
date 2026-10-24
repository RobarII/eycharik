"""End-to-end: a MAX webhook becomes a delivered message through the real adapters.

The chain under test is the deployment's: FastAPI route -> secret check -> ``AcceptInbound`` ->
Postgres (events, jobs, outbox) -> ``JobRunner`` -> ``MessageDispatcher`` -> ``MaxClient`` -> HTTP.
Only the last hop is fake, and it is strict: it checks the request against
``docs/contracts/max-api.md`` instead of accepting anything that happens to be valid JSON.

Skipped unless ``ONBOARDING_TEST_DATABASE`` points at a disposable database.
"""

from __future__ import annotations

import base64
import json
import os
import re
from collections.abc import AsyncIterator, Mapping
from datetime import date
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from pydantic import SecretStr
from sqlalchemy import func, select, text, update

from onboarding.api.app import create_app
from onboarding.app.channels.max.client import MaxClient
from onboarding.app.channels.max.files import MaxFiles
from onboarding.app.composition import SCENARIO_ASSETS_DIR
from onboarding.app.container import Container, build_container
from onboarding.app.db.models import (
    AuditRow,
    ChannelIdentityRow,
    EmployeeRow,
    EventRow,
    InboundFileRow,
    JobRow,
    MessageRow,
    RunRow,
)
from onboarding.app.db.session import Database
from onboarding.app.files.crypto import decrypt
from onboarding.app.files.intake import InboundFileIntake
from onboarding.app.settings import Settings
from onboarding.app.worker.jobs import JobRunner
from onboarding.core.models import Address, Button, Channel, ChatId
from onboarding.ports import OutboundMessage

pytestmark = pytest.mark.integration

SECRET = "e2e-secret"
ADMIN_TOKEN = "admin-token"
TOKEN = "bot-token"
CHAT = 7000001
EMPLOYEE = "1001"
UNLINKED_CHAT = 7000099
FILE_KEY = bytes(range(32))
FILE_KEY_B64 = base64.urlsafe_b64encode(FILE_KEY).decode()
JPEG = b"\xff\xd8\xff\xe0" + b"passport-scan" * 10


def database_url() -> str:
    url = os.environ.get("ONBOARDING_TEST_DATABASE")
    if not url:
        pytest.skip("ONBOARDING_TEST_DATABASE is not set")
    return url


def settings(**overrides: Any) -> Settings:
    return Settings(
        _env_file=None,
        database_url=database_url(),
        channels="max",
        max_webhook_secret=SECRET,
        max_bot_token=TOKEN,
        max_base_url="https://max.test",
        llm_provider="extractive",
        embed_provider="hashing",
        **overrides,
    )


class FakeMax:
    """The MAX Bot API, strict enough to catch a wrong payload and loud about 5xx."""

    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []
        self.violations: list[str] = []
        self.downloads: list[str] = []
        self.uploads = 0
        self.uploaded_bytes = 0
        self.uploaded_files: list[str] = []
        self.fail_sends = 0

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def handle(self, request: httpx.Request) -> httpx.Response:
        if request.headers.get("authorization") != TOKEN:
            self.violations.append(f"bad Authorization on {request.url.path}")
        if request.method == "POST" and request.url.path == "/uploads":
            assert request.url.params["type"] == "image"
            self.uploads += 1
            return httpx.Response(200, json={"url": "https://max.test/upload/1"})
        if request.method == "POST" and request.url.path == "/upload/1":
            body = request.read()
            self.uploaded_bytes += len(body)
            match = re.search(rb'filename="([^"]+)"', body)
            if match is None:
                self.violations.append("upload has no filename")
            else:
                name = match.group(1).decode()
                self.uploaded_files.append(name)
                if not name.endswith(".jpg"):
                    self.violations.append(f"upload is not a jpeg: {name}")
            return httpx.Response(200, json={"token": f"media-{self.uploads}"})
        if request.method == "GET" and request.url.path.startswith("/files/"):
            self.downloads.append(request.url.path)
            return httpx.Response(200, headers={"content-length": str(len(JPEG))}, content=JPEG)
        if request.method == "POST" and request.url.path == "/messages":
            return self._send(request)
        self.violations.append(f"unexpected {request.method} {request.url.path}")
        return httpx.Response(404, json={})

    def _send(self, request: httpx.Request) -> httpx.Response:
        if self.fail_sends > 0:
            self.fail_sends -= 1
            return httpx.Response(500, json={"code": "internal"})
        body = json.loads(request.read())
        chat_id = request.url.params.get("chat_id")
        if not chat_id or not chat_id.isdigit():
            self.violations.append(f"chat_id is {chat_id!r}")
        if request.headers.get("content-type") != "application/json":
            self.violations.append(f"content-type is {request.headers.get('content-type')!r}")
        extra = set(body) - {"text", "attachments", "link"}
        if extra:
            self.violations.append(f"unknown message fields {sorted(extra)}")
        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            self.violations.append("text is empty")
        elif len(text) > 4000:
            self.violations.append(f"text is {len(text)} chars")
        for attachment in body.get("attachments", []):
            self._check_attachment(attachment)
        self.messages.append({"chat_id": int(chat_id), "body": body})
        return httpx.Response(200, json={"message": {"body": {"mid": f"mid-{len(self.messages)}"}}})

    def _check_attachment(self, attachment: Mapping[str, Any]) -> None:
        kind = attachment.get("type")
        if kind == "inline_keyboard":
            buttons = attachment.get("payload", {}).get("buttons")
            if not isinstance(buttons, list) or not buttons:
                self.violations.append("inline_keyboard has no buttons")
                return
            for line in buttons:
                if not isinstance(line, list) or not line:
                    self.violations.append("keyboard row is empty")
                    continue
                for button in line:
                    if button.get("type") != "callback":
                        self.violations.append(f"button type is {button.get('type')!r}")
                    if not button.get("text") or not button.get("payload"):
                        self.violations.append(f"button is missing text/payload: {button}")
        elif kind == "image":
            token = attachment.get("payload", {}).get("token")
            if not isinstance(token, str) or not token:
                self.violations.append(f"image attachment has no token: {attachment}")
        else:
            self.violations.append(f"unexpected attachment type {kind!r}")


def max_client(fake: FakeMax) -> MaxClient:
    return MaxClient(
        base_url="https://max.test",
        token=SecretStr(TOKEN),
        client=httpx.AsyncClient(transport=fake.transport()),
        messages_per_second=1000.0,
        assets_dir=SCENARIO_ASSETS_DIR,
    )


@pytest.fixture
async def database() -> AsyncIterator[Database]:
    db = Database(database_url())
    async with db.session() as session:
        await session.execute(
            text(
                "TRUNCATE messages, jobs, events, questions, audit_log, runs, employees, "
                "channel_identities, inbound_files, kb_chunks, kb_documents, kb_files, "
                "kb_extractions "
                "RESTART IDENTITY CASCADE"
            )
        )
        session.add(
            EmployeeRow(
                id=EMPLOYEE,
                name="Иван Иванов",
                role="Инженер",
                department="ИТ",
                recruiter_id="rec-1",
                started_at=date(2026, 10, 20),
                audience=["all", "dept:it"],
                scenario_id="onboarding_default",
            )
        )
        await session.flush()
        session.add(ChannelIdentityRow(channel="max", external_id=str(CHAT), employee_id=EMPLOYEE))
    yield db
    await db.dispose()


def start_payload(chat_id: int = CHAT) -> dict[str, Any]:
    return {
        "update_type": "bot_started",
        "timestamp": 1_766_000_000_000,
        "chat_id": chat_id,
        "user": {"user_id": chat_id},
    }


def callback_payload(callback_id: str = "cb-1") -> dict[str, Any]:
    return {
        "update_type": "message_callback",
        "timestamp": 1_766_000_001_000,
        "chat_id": CHAT,
        "callback": {
            "callback_id": callback_id,
            "payload": "tone_you",
            "user": {"user_id": CHAT},
        },
        "message": {
            "sender": {"user_id": 1},
            "recipient": {"chat_id": CHAT},
            "body": {"mid": "bot-mid-1"},
        },
    }


async def post(app: FastAPI, payload: Mapping[str, Any], secret: str = SECRET) -> int:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/webhook/max",
            content=json.dumps(payload).encode(),
            headers={"X-Max-Bot-Api-Secret": secret, "Content-Type": "application/json"},
        )
    return response.status_code


async def pump(container: Container, *, ticks: int = 8) -> None:
    runner = JobRunner(
        queue=container.queue,
        service=container.service,
        clock=container.clock,
        audit=container.audit,
        extractor=container.extractor,
        indexer=container.indexer,
        files=container.files,
    )
    for _ in range(ticks):
        handled = await runner.run_once()
        delivered = await container.dispatcher.run_once()
        if handled == 0 and delivered == 0:
            return
    raise AssertionError("the pipeline did not drain")


async def test_a_bot_start_becomes_a_delivered_welcome(database: Database) -> None:
    fake = FakeMax()
    config = settings()
    app = create_app(config)
    async with app.router.lifespan_context(app):
        assert await post(app, start_payload()) == 200
        # MAX retries a delivery it did not see acknowledged; the run must not start twice.
        assert await post(app, start_payload()) == 200
        assert await post(app, start_payload(), secret="wrong") == 401

    container = build_container(config)
    container.senders[Channel.MAX] = max_client(fake)
    try:
        await pump(container)
        async with database.session() as session:
            events = await session.scalar(select(func.count()).select_from(EventRow))
            jobs = await session.scalar(select(func.count()).select_from(JobRow))
            run = await session.scalar(select(RunRow))
            messages = tuple(await session.scalars(select(MessageRow).order_by(MessageRow.id)))

        assert (events, jobs) == (1, 1)
        assert run is not None
        assert run.step_id == "welcome"
        assert [(row.status, row.external_id) for row in messages] == [("sent", "mid-1")]

        assert fake.violations == []
        assert len(fake.messages) == 1
        assert fake.messages[0]["chat_id"] == CHAT
        body = fake.messages[0]["body"]
        assert "Корсик" in body["text"]
        assert [item["type"] for item in body["attachments"]] == ["image", "inline_keyboard"]
        assert body["attachments"][0]["payload"]["token"] == "media-1"
        assert body["attachments"][1]["payload"]["buttons"][0][0]["payload"] == "tone_you"
        assert fake.uploads == 1
        assert fake.uploaded_bytes > 0

        # The button press is a new event and the run advances past the welcome step.
        assert await post(app, callback_payload()) == 200
        await pump(container)
        async with database.session() as session:
            run = await session.scalar(select(RunRow))
            statuses = tuple(
                await session.scalars(select(MessageRow.status).order_by(MessageRow.id))
            )
        assert run is not None
        assert run.step_id == "documents_checklist"
        assert statuses == ("sent", "sent")
        assert len(fake.messages) == 2
        assert "документы" in fake.messages[1]["body"]["text"].lower()
        assert fake.messages[1]["body"]["attachments"][0]["payload"]["token"] == "media-2"
        assert fake.uploads == 2

    finally:
        await container.aclose()


async def _assert_cabinet(app: FastAPI, run_id: str, file_id: object, database: Database) -> None:
    """The cabinet lists the document and hands back exactly the bytes it stored."""
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            detail = await client.get(
                f"/admin/api/v1/runs/{run_id}",
                headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
            )
            download = await client.get(
                f"/admin/api/v1/runs/{run_id}/files/{file_id}",
                headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
            )
    assert detail.status_code == 200
    assert detail.json()["files"][0]["filename"] == "passport.jpg"
    assert detail.json()["files"][0]["status"] == "stored"
    assert download.status_code == 200
    assert download.content == JPEG
    assert download.headers["content-disposition"] == ("attachment; filename*=UTF-8''passport.jpg")
    assert download.headers["cache-control"] == "no-store"
    assert download.headers["x-content-type-options"] == "nosniff"
    async with database.session() as session:
        audited = await session.scalar(
            select(func.count()).select_from(AuditRow).where(AuditRow.name == "file_downloaded")
        )
    assert audited == 1


async def test_a_photo_is_a_receipt_at_the_documents_step(database: Database) -> None:
    fake = FakeMax()
    config = settings(
        inbound_files_key=FILE_KEY_B64, admin_tokens_raw=f"{ADMIN_TOKEN}:hr_admin:hr-1"
    )
    app = create_app(config)
    container = build_container(config)
    container.senders[Channel.MAX] = max_client(fake)
    container.files = InboundFileIntake(
        database=container.database,
        fetcher=MaxFiles(
            client=httpx.AsyncClient(transport=fake.transport()),
            token=SecretStr(TOKEN),
            platform_host="max.test",
            max_bytes=1024 * 1024,
        ),
        audit=container.audit,
        key=FILE_KEY,
        max_bytes=1024 * 1024,
    )
    try:
        async with app.router.lifespan_context(app):
            assert await post(app, start_payload()) == 200
            await pump(container)
            assert await post(app, callback_payload()) == 200
            await pump(container)
            async with database.session() as session:
                run = await session.scalar(select(RunRow))
            assert run is not None
            assert run.step_id == "documents_checklist"

            # A passport photo with no caption is the receipt this step asks for: the run moves on.
            assert (
                await post(
                    app,
                    {
                        "update_type": "message_created",
                        "timestamp": 1_766_000_003_000,
                        "chat_id": CHAT,
                        "user": {"user_id": CHAT},
                        "message": {
                            "sender": {"user_id": CHAT},
                            "recipient": {"chat_id": CHAT},
                            "body": {
                                "mid": "mid-photo",
                                "attachments": [
                                    {
                                        "type": "image",
                                        "payload": {
                                            "token": "photo-token-1",
                                            "url": "https://max.test/files/photo-token-1",
                                            "filename": "passport.jpg",
                                            "size": len(JPEG),
                                        },
                                    }
                                ],
                            },
                        },
                    },
                )
                == 200
            )
            await pump(container)

        async with database.session() as session:
            run = await session.scalar(select(RunRow))
            events = await session.scalar(
                select(func.count()).select_from(EventRow).where(EventRow.key == "max:mid-photo")
            )
            stored = await session.scalar(select(InboundFileRow))
            run_id = run.id if run is not None else None
        assert run is not None
        assert run.step_id == "day_before"
        assert events == 1
        assert fake.downloads == ["/files/photo-token-1"]
        assert stored is not None
        assert stored.filename == "passport.jpg"
        assert stored.status == "stored"
        assert stored.content is not None
        assert b"passport-scan" not in stored.content
        assert decrypt(FILE_KEY, stored.content) == JPEG
        assert fake.violations == []

        await _assert_cabinet(app, run_id, stored.id, database)
    finally:
        await container.aclose()


async def test_a_typed_start_command_opens_the_run(database: Database) -> None:
    fake = FakeMax()
    config = settings()
    app = create_app(config)
    async with app.router.lifespan_context(app):
        assert (
            await post(
                app,
                {
                    "update_type": "message_created",
                    "timestamp": 1_766_000_002_000,
                    "chat_id": CHAT,
                    "user": {"user_id": CHAT},
                    "message": {
                        "sender": {"user_id": CHAT},
                        "recipient": {"chat_id": CHAT},
                        "body": {"mid": "mid-start", "text": "/start"},
                    },
                },
            )
            == 200
        )
    container = build_container(config)
    container.senders[Channel.MAX] = max_client(fake)
    try:
        await pump(container)
        async with database.session() as session:
            run = await session.scalar(select(RunRow))
            messages = await session.scalar(select(func.count()).select_from(MessageRow))
    finally:
        await container.aclose()

    assert run is not None
    assert run.step_id == "welcome"
    assert messages == 1
    assert fake.violations == []


async def test_run_detail_names_the_messenger_account(database: Database) -> None:
    # The card must print the messenger account; the HR id is not an address in MAX.
    fake = FakeMax()
    config = settings(admin_tokens_raw=f"{ADMIN_TOKEN}:hr_admin:hr-1")
    app = create_app(config)
    container = build_container(config)
    container.senders[Channel.MAX] = max_client(fake)
    try:
        async with app.router.lifespan_context(app):
            assert await post(app, start_payload()) == 200
        await pump(container)
        async with database.session() as session:
            run_id = await session.scalar(select(RunRow.id))
        assert run_id is not None
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    f"/admin/api/v1/runs/{run_id}",
                    headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
                )
    finally:
        await container.aclose()

    assert response.status_code == 200
    payload = response.json()
    assert payload["employee_id"] == EMPLOYEE
    assert payload["channels"] == [
        {
            "channel": "max",
            "external_id": str(CHAT),
            "linked_at": payload["channels"][0]["linked_at"],
        }
    ]


async def test_a_failed_send_is_retried_by_the_dispatcher(database: Database) -> None:
    fake = FakeMax()
    config = settings()
    container = build_container(config)
    container.senders[Channel.MAX] = max_client(fake)
    address = Address(channel=Channel.MAX, chat_id=ChatId(CHAT))
    try:
        await container.outbox.send(
            OutboundMessage(address=address, text="привет", keyboard=((Button(id="a", text="A"),),))
        )
        fake.fail_sends = 1
        await container.dispatcher.run_once()
        async with database.session() as session:
            row = await session.scalar(select(MessageRow))
            assert row is not None
            assert (row.status, row.attempts) == ("pending", 1)
            assert "HTTP 500" in (row.last_error or "")
            # Time passes: the backoff has elapsed, the next tick delivers the same row.
            await session.execute(update(MessageRow).values(available_at=func.now()))
        await container.dispatcher.run_once()
        async with database.session() as session:
            row = await session.scalar(select(MessageRow))
        assert row is not None
        assert (row.status, row.attempts, row.external_id) == ("sent", 1, "mid-1")
        assert len(fake.messages) == 1
        assert fake.violations == []
    finally:
        await container.aclose()


async def test_an_unlinked_account_is_audited_and_gets_no_run(
    database: Database,
) -> None:
    fake = FakeMax()
    config = settings()
    app = create_app(config)
    async with app.router.lifespan_context(app):
        assert await post(app, start_payload(chat_id=UNLINKED_CHAT)) == 200

    container = build_container(config)
    container.senders[Channel.MAX] = max_client(fake)
    try:
        await pump(container)
        async with database.session() as session:
            runs = await session.scalar(select(func.count()).select_from(RunRow))
            jobs = await session.scalar(select(func.count()).select_from(JobRow))
            audited = await session.scalar(
                select(AuditRow.name).where(AuditRow.name == "unlinked_channel_user")
            )
    finally:
        await container.aclose()

    assert (runs, jobs) == (0, 0)
    assert audited == "unlinked_channel_user"
    assert fake.messages == []


def test_the_strict_fake_catches_a_payload_it_should_reject() -> None:
    """The gate has to have power: a wrong request must produce a violation, not a pass."""
    fake = FakeMax()
    request = httpx.Request(
        "POST",
        "https://max.test/messages?chat_id=1",
        json={"text": "", "attachments": [{"type": "inline_keyboard", "payload": {"buttons": []}}]},
        headers={"Authorization": "wrong"},
    )

    response = fake.handle(request)

    assert response.status_code == 200
    assert any("Authorization" in violation for violation in fake.violations)
    assert any("text is empty" in violation for violation in fake.violations)
    assert any("no buttons" in violation for violation in fake.violations)
