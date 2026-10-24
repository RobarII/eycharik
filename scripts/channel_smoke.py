#!/usr/bin/env python3
"""Drive a whole scenario through a live messenger and check what actually happened.

The smoke fabricates updates exactly as the messenger would post them — same JSON, same secret
header — and then reads the database: an event, a job, a step transition, an outbound row, and the
message id the messenger returned. An ``ok`` here means the message reached the messenger, not
merely that the worker queued it.

Environment: ``TELEGRAM_WEBHOOK_SECRET`` (or ``VK_WEBHOOK_SECRET`` with ``VK_GROUP_ID``),
``DATABASE_URL``, and ``HTTPS_PROXY`` or ``ALL_PROXY`` when ``api.telegram.org`` is not reachable
directly.

Example::

    TELEGRAM_WEBHOOK_SECRET=... DATABASE_URL=... \\
        uv run python scripts/channel_smoke.py \\
        --base-url https://host --chat-id 5596309088 --reset

    VK_WEBHOOK_SECRET=... DATABASE_URL=... \\
        uv run python scripts/channel_smoke.py --channel vk \\
        --base-url https://host --chat-id 2000000123 --group-id 242545422 --reset
"""

from __future__ import annotations

import argparse
import asyncio
import itertools
import os
import sys
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from onboarding.app.scenarios import ScenarioCatalog  # noqa: E402
from onboarding.core.models import (  # noqa: E402
    Expects,
    Question,
    QuestionKind,
    Scenario,
    Step,
    StepKind,
)

SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"  # noqa: S105 - a header name
SETTLE_SECONDS = 25.0
POLL_SECONDS = 0.4
MAX_TURNS = 80
BODY_CAP = 1_000_000


class Reporter:
    """Collects checks and prints them in order."""

    def __init__(self) -> None:
        self.rows: list[tuple[bool, str, str]] = []

    def check(self, ok: bool, name: str, detail: str = "") -> bool:
        self.rows.append((ok, name, detail))
        return ok

    def report(self) -> int:
        for ok, name, detail in self.rows:
            mark = "ok  " if ok else "FAIL"
            print(f"{mark}  {name}{f'  ({detail})' if detail else ''}")
        failed = [row for row in self.rows if not row[0]]
        print(f"\n{len(self.rows) - len(failed)}/{len(self.rows)} checks passed")
        return 1 if failed else 0


class Updates:
    """Posts Telegram-shaped updates to the public webhook and counts them."""

    channel = "telegram"
    text_limit = 4096
    # Telegram authenticates with a header, so a body that is not JSON reaches the parser and is
    # named as such. VK carries the secret inside the body and cannot do that (see ``VkUpdates``).
    non_json_status = 400

    def __init__(self, http: httpx.AsyncClient, url: str, secret: str, chat_id: int) -> None:
        self._http = http
        self._url = url
        self._secret = secret
        self._chat_id = chat_id
        # Unique per run: the dedupe table remembers every update id ever seen, and a repeated
        # id would be swallowed as a redelivery instead of exercising the webhook.
        self._ids = itertools.count(int(time.time()) * 1000)
        self.sent = 0

    @property
    def http(self) -> httpx.AsyncClient:
        return self._http

    @property
    def url(self) -> str:
        return self._url

    @property
    def secret(self) -> str:
        return self._secret

    def envelope(self, **fields: Any) -> dict[str, Any]:
        return {"update_id": next(self._ids), **fields}

    def sender(self) -> dict[str, Any]:
        return {"id": self._chat_id, "is_bot": False, "first_name": "Smoke"}

    def chat(self) -> dict[str, Any]:
        return {"id": self._chat_id, "type": "private"}

    async def post(
        self, payload: dict[str, Any], *, secret: str | None = None, raw: bytes | None = None
    ) -> httpx.Response:
        self.sent += 1
        headers = {SECRET_HEADER: secret if secret is not None else self._secret}
        body = raw if raw is not None else None
        return await self._http.post(
            self._url,
            headers={**headers, "content-type": "application/json"},
            json=payload if body is None else None,
            content=body,
        )

    def payload_start(self) -> dict[str, Any]:
        return self.payload_message("/start")

    def payload_message(self, value: str) -> dict[str, Any]:
        return self.envelope(
            message={
                "message_id": next(self._ids),
                "date": _now_ts(),
                "chat": self.chat(),
                "from": self.sender(),
                "text": value,
            }
        )

    def payload_document(self) -> dict[str, Any]:
        return self.envelope(
            message={
                "message_id": next(self._ids),
                "date": _now_ts(),
                "chat": self.chat(),
                "from": self.sender(),
                "document": {"file_id": "smoke-file", "file_name": "passport.pdf"},
            }
        )

    def payload_button(self, button_id: str) -> dict[str, Any]:
        return self.envelope(
            callback_query={
                "id": f"cb-{next(self._ids)}",
                "from": self.sender(),
                "data": button_id,
                "message": {
                    "message_id": next(self._ids),
                    "date": _now_ts(),
                    "chat": self.chat(),
                },
            }
        )

    def with_chat(self, chat_id: int) -> Updates:
        """The same channel, a different chat: used to probe an unlinked account."""
        return Updates(self._http, self._url, self._secret, chat_id)

    async def start(self) -> httpx.Response:
        return await self.post(self.payload_start())

    async def message(self, value: str) -> httpx.Response:
        return await self.post(self.payload_message(value))

    async def document(self) -> httpx.Response:
        return await self.post(self.payload_document())

    async def button(self, button_id: str) -> httpx.Response:
        return await self.post(self.payload_button(button_id))


class VkUpdates:
    """Posts VK Callback API payloads: the same envelope, with the secret in the body.

    VK has no update id counter; ``event_id`` is the dedupe key, so every payload carries a fresh
    one and a redelivery is expressed by posting the very same payload twice.
    """

    channel = "vk"
    text_limit = 4096
    # The secret lives in the payload, so a body that is not JSON cannot be verified at all: the
    # refusal is a 401, not a 400.
    non_json_status = 401

    def __init__(
        self,
        http: httpx.AsyncClient,
        url: str,
        secret: str,
        chat_id: int,
        group_id: int,
    ) -> None:
        self._http = http
        self._url = url
        self._secret = secret
        self._chat_id = chat_id
        self._group_id = group_id
        self._ids = itertools.count(int(time.time()) * 1000)
        self.sent = 0

    @property
    def http(self) -> httpx.AsyncClient:
        return self._http

    @property
    def url(self) -> str:
        return self._url

    @property
    def secret(self) -> str:
        return self._secret

    def _event_id(self) -> str:
        return f"smoke{next(self._ids):x}"

    def envelope(self, kind: str, **object_fields: Any) -> dict[str, Any]:
        return {
            "type": kind,
            "group_id": self._group_id,
            "event_id": self._event_id(),
            "v": "5.199",
            "secret": self._secret,
            "object": object_fields,
        }

    def message_object(self, **fields: Any) -> dict[str, Any]:
        return {
            "from_id": self._chat_id,
            "peer_id": self._chat_id,
            "date": _now_ts(),
            "conversation_message_id": next(self._ids),
            **fields,
        }

    def payload_start(self) -> dict[str, Any]:
        return self.payload_message("/start")

    def payload_message(self, value: str) -> dict[str, Any]:
        return self.envelope("message_new", message=self.message_object(text=value))

    def payload_document(self) -> dict[str, Any]:
        document = {
            "id": next(self._ids),
            "owner_id": self._chat_id,
            "title": "passport",
            "ext": "pdf",
            "url": "https://example.invalid/passport.pdf",
            "access_key": "smoke-file",
        }
        return self.envelope(
            "message_new",
            message=self.message_object(attachments=[{"type": "doc", "doc": document}]),
        )

    def payload_button(self, button_id: str) -> dict[str, Any]:
        return self.envelope(
            "message_event",
            user_id=self._chat_id,
            peer_id=self._chat_id,
            event_id=self._event_id(),
            conversation_message_id=next(self._ids),
            payload={"id": button_id},
        )

    async def post(
        self, payload: dict[str, Any], *, secret: str | None = None, raw: bytes | None = None
    ) -> httpx.Response:
        self.sent += 1
        body = dict(payload)
        presented = self._secret if secret is None else secret
        if presented:
            body["secret"] = presented
        else:
            # An empty secret is a delivery with the field absent, not with an empty one.
            body.pop("secret", None)
        return await self._http.post(
            self._url,
            headers={"content-type": "application/json"},
            json=body if raw is None else None,
            content=raw,
        )

    def with_chat(self, chat_id: int) -> VkUpdates:
        """The same community, a different peer: used to probe an unlinked account."""
        return VkUpdates(self._http, self._url, self._secret, chat_id, self._group_id)

    async def start(self) -> httpx.Response:
        return await self.post(self.payload_start())

    async def message(self, value: str) -> httpx.Response:
        return await self.post(self.payload_message(value))

    async def document(self) -> httpx.Response:
        return await self.post(self.payload_document())

    async def button(self, button_id: str) -> httpx.Response:
        return await self.post(self.payload_button(button_id))


UpdatesLike = Updates | VkUpdates


def _now_ts() -> int:
    return int(datetime.now(UTC).timestamp())


async def _first(engine: AsyncEngine, sql: str, **params: Any) -> dict[str, Any] | None:
    async with engine.connect() as connection:
        row = (await connection.execute(text(sql), params)).mappings().first()
    return cast(dict[str, Any], dict(row)) if row is not None else None


async def _scalar(engine: AsyncEngine, sql: str, **params: Any) -> int:
    async with engine.connect() as connection:
        value = await connection.scalar(text(sql), params)
    return int(value or 0)


async def _active_run(engine: AsyncEngine, channel: str, chat_id: int) -> dict[str, Any] | None:
    return await _first(
        engine,
        "select id, employee_id, channel, chat_id, step_id, question_index, status"
        " from runs where channel = :channel and chat_id = :chat and status = 'active'",
        channel=channel,
        chat=chat_id,
    )


async def _message_stats(engine: AsyncEngine, channel: str, chat_id: int) -> dict[str, int]:
    row = await _first(
        engine,
        "select count(*) as total,"
        " count(*) filter (where status = 'sent') as sent,"
        " count(*) filter (where status = 'failed') as failed,"
        " count(*) filter (where external_id is null) as without_id,"
        " coalesce(max(length(text)), 0) as longest"
        " from messages where channel = :channel and chat_id = :chat",
        channel=channel,
        chat=chat_id,
    )
    return {key: int(value) for key, value in (row or {}).items()}


async def wait_for(
    predicate: Callable[[], Awaitable[bool]], timeout: float = SETTLE_SECONDS
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if await predicate():
            return True
        await asyncio.sleep(POLL_SECONDS)
    return False


def _buttons(step: Step) -> list[str]:
    return [button.id for row in step.keyboard for button in row]


def _answer_payload(question: Question) -> tuple[str, str]:
    """Return (kind, value) for the next survey question: a button id or a text."""
    if question.kind is QuestionKind.CHOICE and question.options:
        return "button", f"q_{question.id}_{question.options[0].id}"
    if question.kind is QuestionKind.SCALE:
        return "text", "9"
    return "text", "Коллеги показали, где что лежит, и это помогло."


async def _answer(
    step: Step, run: dict[str, Any], updates: UpdatesLike, chat_id: int, *, trouble: bool = False
) -> tuple[str, str]:
    """Send the event this step is waiting for. Returns a label and the outbound call."""
    if step.kind is StepKind.SURVEY:
        index = int(run["question_index"])
        question = step.questions[min(index, len(step.questions) - 1)]
        kind, value = _answer_payload(question)
        if kind == "button":
            await updates.button(value)
            return f"survey/{question.id}", value
        await updates.message(value)
        return f"survey/{question.id}", "text"

    if step.expects is Expects.FILE:
        await updates.document()
        return "document", "passport.pdf"
    buttons = _buttons(step)
    if step.expects is Expects.BUTTON and buttons:
        chosen = buttons[-1] if trouble else buttons[0]
        await updates.button(chosen)
        return f"button {chosen}", chosen
    await updates.message("Всё передал рекрутёру, документы в порядке.")
    return "message", "text"


async def drive(
    engine: AsyncEngine,
    scenario: Scenario,
    updates: UpdatesLike,
    reporter: Reporter,
    *,
    chat_id: int,
    timeout: float,
    trouble: bool = False,
) -> None:
    """Walk the scenario until the run is no longer active, checking every transition."""
    probe_start = True
    for _ in range(MAX_TURNS):
        run = await _active_run(engine, updates.channel, chat_id)
        if run is None:
            return
        step = scenario.step(cast(str, run["step_id"]))
        if step.kind is StepKind.SEND:
            await asyncio.sleep(POLL_SECONDS)
            continue
        marker = (step.id, int(run["question_index"]))
        label, _value = await _answer(step, run, updates, chat_id, trouble=trouble)

        async def moved(marker: tuple[str, int] = marker) -> bool:
            now = await _active_run(engine, updates.channel, chat_id)
            if now is None:
                return True
            return (cast(str, now["step_id"]), int(now["question_index"])) != marker

        settled = await wait_for(moved, timeout)
        after = await _active_run(engine, updates.channel, chat_id)
        where = "run closed" if after is None else f"{after['step_id']}[{after['question_index']}]"
        reporter.check(settled, f"{step.id} <- {label}", where)
        if not settled:
            return
        if probe_start:
            probe_start = False
            await check_second_start(engine, scenario, updates, reporter, chat_id=chat_id)


async def check_delivery(
    engine: AsyncEngine,
    http: httpx.AsyncClient,
    updates: UpdatesLike,
    token: str,
    reporter: Reporter,
    *,
    chat_id: int,
) -> None:
    """Every outbound row must be accepted by the messenger and fit the channel's text cap."""

    async def drained() -> bool:
        now = await _message_stats(engine, updates.channel, chat_id)
        return now["total"] == now["sent"] + now["failed"]

    await wait_for(drained)
    stats = await _message_stats(engine, updates.channel, chat_id)
    reporter.check(
        stats["total"] > 0 and stats["sent"] == stats["total"],
        f"every message was accepted by {updates.channel}",
        f"{stats['sent']}/{stats['total']} sent, {stats['failed']} failed",
    )
    reporter.check(
        stats["without_id"] == 0,
        "every message carries the messenger id",
        f"{stats['without_id']} without id",
    )
    reporter.check(
        stats["longest"] <= updates.text_limit,
        f"text fits the {updates.channel} limit",
        str(stats["longest"]),
    )
    if not token or updates.channel != "telegram":
        return
    async with httpx.AsyncClient(timeout=20) as talk:
        chat = await talk.get(
            f"https://api.telegram.org/bot{token}/getChat", params={"chat_id": chat_id}
        )
    reporter.check(chat.json().get("ok") is True, "the bot can see the chat")


def _bogus() -> str:
    return "not-the-real-secret"


async def check_negative(
    engine: AsyncEngine, updates: UpdatesLike, reporter: Reporter, *, chat_id: int
) -> None:
    """The webhook must refuse what it cannot trust and ignore what it cannot attribute."""
    anonymous = await updates.post(updates.payload_message(""), secret="")
    reporter.check(
        anonymous.status_code == 401, "missing secret is refused", str(anonymous.status_code)
    )
    wrong = await updates.post(updates.payload_message(""), secret=_bogus())
    reporter.check(wrong.status_code == 401, "wrong secret is refused", str(wrong.status_code))

    broken = await http_post_raw(updates, b"{not json")
    reporter.check(
        broken.status_code == updates.non_json_status,
        f"non-JSON body is a {updates.non_json_status}",
        str(broken.status_code),
    )

    huge = await http_post_raw(updates, b"{" + b" " * BODY_CAP + b"}")
    reporter.check(huge.status_code == 413, "oversized body is a 413", str(huge.status_code))

    # Not a messenger this deployment knows at all, so the route itself must refuse it.
    unknown = await http_post_raw(
        updates, b'{"type": "message_new"}', path="/webhook/whatsapp", header=updates.secret
    )
    reporter.check(
        unknown.status_code == 404,
        "a channel that is off is not served",
        str(unknown.status_code),
    )

    stranger = 999_000_001
    before = await _scalar(
        engine,
        "select count(*) from runs where channel = :channel and chat_id = :chat",
        channel=updates.channel,
        chat=stranger,
    )
    stranger_updates = updates.with_chat(stranger)
    answer = await stranger_updates.start()
    audited = await _scalar(
        engine,
        "select count(*) from audit_log where name = 'unlinked_channel_user'"
        " and fields->>'chat_id' = :chat",
        chat=str(stranger),
    )
    after = await _scalar(
        engine,
        "select count(*) from runs where channel = :channel and chat_id = :chat",
        channel=updates.channel,
        chat=stranger,
    )
    reporter.check(
        answer.status_code == 200 and before == after == 0 and audited >= 1,
        "an unlinked account is acknowledged, audited, and gets no run",
        f"http {answer.status_code}, runs {after}, audits {audited}",
    )


async def http_post_raw(
    updates: UpdatesLike, body: bytes, *, path: str = "", header: str = ""
) -> httpx.Response:
    if not path:
        return await updates.post({}, raw=body)
    base = updates.url.rsplit("/webhook/", 1)[0]
    return await updates.http.post(f"{base}{path}", headers={SECRET_HEADER: header}, content=body)


async def check_dedupe(
    engine: AsyncEngine, updates: UpdatesLike, reporter: Reporter, *, chat_id: int
) -> None:
    """The same update twice is one event, one job, one answer."""
    before_events = await _scalar(
        engine, "select count(*) from events where key like :prefix", prefix=f"{updates.channel}:%"
    )
    payload = updates.payload_start()
    await updates.post(payload)
    await updates.post(payload)
    after_events = await _scalar(
        engine, "select count(*) from events where key like :prefix", prefix=f"{updates.channel}:%"
    )
    reporter.check(
        after_events - before_events == 1,
        "a redelivered update is one event",
        f"{after_events - before_events} events",
    )


async def check_second_start(
    engine: AsyncEngine,
    scenario: Scenario,
    updates: UpdatesLike,
    reporter: Reporter,
    *,
    chat_id: int,
) -> None:
    """A second start in the same chat must not restart or duplicate anything."""
    run = await _active_run(engine, updates.channel, chat_id)
    if run is None:
        reporter.check(False, "a second start keeps the run", "no active run to test")
        return
    step_before = cast(str, run["step_id"])
    messages_before = (await _message_stats(engine, updates.channel, chat_id))["total"]
    await updates.start()
    await asyncio.sleep(2.0)
    run_after = await _active_run(engine, updates.channel, chat_id)
    step_after = cast(str, cast(dict[str, Any], run_after)["step_id"]) if run_after else "closed"
    messages_after = (await _message_stats(engine, updates.channel, chat_id))["total"]
    reporter.check(
        step_after == step_before and messages_after == messages_before,
        "a second start neither restarts nor duplicates",
        f"{step_before} -> {step_after}, messages {messages_before} -> {messages_after}",
    )
    reporter.check(step_after in set(scenario.steps), "the run is still on its script")


async def reset(engine: AsyncEngine, channel: str, chat_id: int) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text("delete from messages where channel = :channel and chat_id = :chat"),
            {"channel": channel, "chat": chat_id},
        )
        await connection.execute(
            text("delete from runs where channel = :channel and chat_id = :chat"),
            {"channel": channel, "chat": chat_id},
        )
        await connection.execute(
            text("delete from jobs where payload->>'chat_id' = :chat"), {"chat": str(chat_id)}
        )
        await connection.execute(
            text("delete from events where key like :prefix"), {"prefix": f"{channel}:%"}
        )


async def smoke(args: argparse.Namespace, secret: str, database_url: str) -> int:
    engine = create_async_engine(database_url)
    reporter = Reporter()
    scenario = ScenarioCatalog.load(ROOT / "apps" / "api" / "onboarding" / "scenarios").active(
        args.scenario
    )
    url = f"{args.base_url.rstrip('/')}/webhook/{args.channel}"
    async with httpx.AsyncClient(timeout=30) as http:
        updates: UpdatesLike
        if args.channel == "vk":
            updates = VkUpdates(http, url, secret, args.chat_id, args.group_id)
        else:
            updates = Updates(http, url, secret, args.chat_id)
        try:
            if args.reset:
                await reset(engine, updates.channel, args.chat_id)
                reporter.check(True, "run reset", f"chat {args.chat_id}")

            risks_before = await _scalar(
                engine, "select count(*) from audit_log where name = 'risk_assessed'"
            )
            started = await updates.start()

            async def running() -> bool:
                return await _active_run(engine, updates.channel, args.chat_id) is not None

            welcomed = await wait_for(running)
            run = await _active_run(engine, updates.channel, args.chat_id)
            reporter.check(
                started.status_code == 200 and welcomed,
                "start opens a run",
                f"http {started.status_code}, step {run['step_id'] if run else 'none'}",
            )

            await drive(
                engine,
                scenario,
                updates,
                reporter,
                chat_id=args.chat_id,
                timeout=args.timeout,
                trouble=args.branch == "trouble",
            )

            finished = await _first(
                engine,
                "select status from runs where channel = :channel and chat_id = :chat"
                " order by entered_at desc limit 1",
                channel=updates.channel,
                chat=args.chat_id,
            )
            reporter.check(
                bool(finished) and finished["status"] == "completed",
                "the scenario runs to its end",
                cast(dict[str, Any], finished or {}).get("status", "no run"),
            )

            if args.branch == "trouble":
                risks_after = await _scalar(
                    engine, "select count(*) from audit_log where name = 'risk_assessed'"
                )
                reporter.check(
                    risks_after > risks_before,
                    "an unhappy survey answer is scored for risk",
                    f"{risks_after - risks_before} assessments",
                )

            await check_delivery(engine, http, updates, args.token, reporter, chat_id=args.chat_id)
            await check_negative(engine, updates, reporter, chat_id=args.chat_id)
            await check_dedupe(engine, updates, reporter, chat_id=args.chat_id)
        finally:
            await engine.dispose()
    return reporter.report()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="end-to-end smoke for one messenger channel")
    parser.add_argument("--base-url", required=True, help="public origin, e.g. https://host")
    parser.add_argument("--chat-id", type=int, required=True, help="the linked chat to drive")
    parser.add_argument("--channel", choices=["telegram", "vk"], default="telegram")
    parser.add_argument("--scenario", default="onboarding_plant")
    parser.add_argument("--token", default=os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    parser.add_argument(
        "--group-id",
        type=int,
        default=int(os.environ.get("VK_GROUP_ID", "0") or 0),
        help="VK community id; required when --channel is vk",
    )
    parser.add_argument("--timeout", type=float, default=SETTLE_SECONDS)
    parser.add_argument("--reset", action="store_true", help="delete this chat's run first")
    parser.add_argument(
        "--branch",
        choices=["calm", "trouble"],
        default="calm",
        help="which keyboard option to press when a step offers a choice",
    )
    args = parser.parse_args(argv)

    secrets = {
        "telegram": ("TELEGRAM_WEBHOOK_SECRET", os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")),
        "vk": ("VK_WEBHOOK_SECRET", os.environ.get("VK_WEBHOOK_SECRET", "")),
    }
    variable, secret = secrets[args.channel]
    database_url = os.environ.get("DATABASE_URL", "")
    if not secret or not database_url:
        parser.error(f"{variable} and DATABASE_URL must be set")
    if args.channel == "vk" and not args.group_id:
        parser.error("--group-id (or VK_GROUP_ID) must be set for vk")
    return asyncio.run(smoke(args, secret, database_url))


if __name__ == "__main__":
    raise SystemExit(main())
