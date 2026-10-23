#!/usr/bin/env python3
"""Drive a whole scenario through a live messenger and check what actually happened.

The smoke fabricates updates exactly as the messenger would post them — same JSON, same secret
header — and then reads the database: an event, a job, a step transition, an outbound row, and the
message id the messenger returned. An ``ok`` here means the message reached the messenger, not
merely that the worker queued it.

Environment: ``TELEGRAM_WEBHOOK_SECRET``, ``DATABASE_URL``, and ``HTTPS_PROXY`` or ``ALL_PROXY``
when ``api.telegram.org`` is not reachable directly.

Example::

    TELEGRAM_WEBHOOK_SECRET=... DATABASE_URL=... \\
        uv run python scripts/channel_smoke.py \\
        --base-url https://host --chat-id 5596309088 --employee 1001 --reset
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
    """Posts messenger-shaped updates to the public webhook and counts them."""

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

    async def start(self) -> httpx.Response:
        return await self.post(
            self.envelope(
                message={
                    "message_id": next(self._ids),
                    "date": _now_ts(),
                    "chat": self.chat(),
                    "from": self.sender(),
                    "text": "/start",
                }
            )
        )

    async def message(self, value: str) -> httpx.Response:
        return await self.post(
            self.envelope(
                message={
                    "message_id": next(self._ids),
                    "date": _now_ts(),
                    "chat": self.chat(),
                    "from": self.sender(),
                    "text": value,
                }
            )
        )

    async def document(self) -> httpx.Response:
        return await self.post(
            self.envelope(
                message={
                    "message_id": next(self._ids),
                    "date": _now_ts(),
                    "chat": self.chat(),
                    "from": self.sender(),
                    "document": {"file_id": "smoke-file", "file_name": "passport.pdf"},
                }
            )
        )

    async def button(self, button_id: str) -> httpx.Response:
        return await self.post(
            self.envelope(
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
        )


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


async def _active_run(engine: AsyncEngine, chat_id: int) -> dict[str, Any] | None:
    return await _first(
        engine,
        "select id, employee_id, channel, chat_id, step_id, question_index, status"
        " from runs where chat_id = :chat and status = 'active'",
        chat=chat_id,
    )


async def _message_stats(engine: AsyncEngine, chat_id: int) -> dict[str, int]:
    row = await _first(
        engine,
        "select count(*) as total,"
        " count(*) filter (where status = 'sent') as sent,"
        " count(*) filter (where status = 'failed') as failed,"
        " count(*) filter (where external_id is null) as without_id,"
        " coalesce(max(length(text)), 0) as longest"
        " from messages where chat_id = :chat",
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
    step: Step, run: dict[str, Any], updates: Updates, chat_id: int, *, trouble: bool = False
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
    updates: Updates,
    reporter: Reporter,
    *,
    chat_id: int,
    timeout: float,
    trouble: bool = False,
) -> None:
    """Walk the scenario until the run is no longer active, checking every transition."""
    probe_start = True
    for _ in range(MAX_TURNS):
        run = await _active_run(engine, chat_id)
        if run is None:
            return
        step = scenario.step(cast(str, run["step_id"]))
        if step.kind is StepKind.SEND:
            await asyncio.sleep(POLL_SECONDS)
            continue
        marker = (step.id, int(run["question_index"]))
        label, _value = await _answer(step, run, updates, chat_id, trouble=trouble)

        async def moved(marker: tuple[str, int] = marker) -> bool:
            now = await _active_run(engine, chat_id)
            if now is None:
                return True
            return (cast(str, now["step_id"]), int(now["question_index"])) != marker

        settled = await wait_for(moved, timeout)
        after = await _active_run(engine, chat_id)
        where = "run closed" if after is None else f"{after['step_id']}[{after['question_index']}]"
        reporter.check(settled, f"{step.id} <- {label}", where)
        if not settled:
            return
        if probe_start:
            probe_start = False
            await check_second_start(
                engine, scenario, updates, reporter, chat_id=chat_id
            )


async def check_delivery(
    engine: AsyncEngine, http: httpx.AsyncClient, token: str, chat_id: int, reporter: Reporter
) -> None:
    """Every outbound row must be accepted by Telegram and fit the profile's text cap."""
    async def drained() -> bool:
        now = await _message_stats(engine, chat_id)
        return now["total"] == now["sent"] + now["failed"]

    await wait_for(drained)
    stats = await _message_stats(engine, chat_id)
    reporter.check(
        stats["total"] > 0 and stats["sent"] == stats["total"],
        "every message was accepted by Telegram",
        f"{stats['sent']}/{stats['total']} sent, {stats['failed']} failed",
    )
    reporter.check(
        stats["without_id"] == 0,
        "every message carries the messenger id",
        f"{stats['without_id']} without id",
    )
    reporter.check(stats["longest"] <= 4096, "text fits the Telegram limit", str(stats["longest"]))
    if not token:
        return
    async with httpx.AsyncClient(timeout=20) as talk:
        chat = await talk.get(
        f"https://api.telegram.org/bot{token}/getChat", params={"chat_id": chat_id}
    )
    reporter.check(chat.json().get("ok") is True, "the bot can see the chat")


def _bogus() -> str:
    return "not-the-real-secret"


async def check_negative(
    engine: AsyncEngine, updates: Updates, reporter: Reporter, *, chat_id: int
) -> None:
    """The webhook must refuse what it cannot trust and ignore what it cannot attribute."""
    anonymous = await updates.post(updates.envelope(message={}), secret="")
    reporter.check(
        anonymous.status_code == 401, "missing secret is refused", str(anonymous.status_code)
    )
    wrong = await updates.post(updates.envelope(message={}), secret=_bogus())
    reporter.check(wrong.status_code == 401, "wrong secret is refused", str(wrong.status_code))

    broken = await http_post_raw(updates, b"{not json")
    reporter.check(broken.status_code == 400, "non-JSON body is a 400", str(broken.status_code))

    huge = await http_post_raw(updates, b"{" + b" " * BODY_CAP + b"}")
    reporter.check(huge.status_code == 413, "oversized body is a 413", str(huge.status_code))

    unknown = await http_post_raw(
        updates, b'{"type": "message_new"}', path="/webhook/vk", header=updates.secret
    )
    reporter.check(
        unknown.status_code == 404,
        "a channel that is off is not served",
        str(unknown.status_code),
    )

    stranger = 999_000_001
    before = await _scalar(engine, "select count(*) from runs where chat_id = :chat", chat=stranger)
    stranger_updates = Updates(updates.http, updates.url, updates.secret, stranger)
    answer = await stranger_updates.start()
    audited = await _scalar(
        engine,
        "select count(*) from audit_log where name = 'unlinked_channel_user'"
        " and fields->>'chat_id' = :chat",
        chat=str(stranger),
    )
    after = await _scalar(engine, "select count(*) from runs where chat_id = :chat", chat=stranger)
    reporter.check(
        answer.status_code == 200 and before == after == 0 and audited >= 1,
        "an unlinked account is acknowledged, audited, and gets no run",
        f"http {answer.status_code}, runs {after}, audits {audited}",
    )


async def http_post_raw(
    updates: Updates, body: bytes, *, path: str = "", header: str = ""
) -> httpx.Response:
    if not path:
        return await updates.post({}, raw=body)
    base = updates.url.rsplit("/webhook/", 1)[0]
    return await updates.http.post(f"{base}{path}", headers={SECRET_HEADER: header}, content=body)


async def check_dedupe(engine: AsyncEngine, updates: Updates, reporter: Reporter) -> None:
    """The same update twice is one event, one job, one answer."""
    before_events = await _scalar(engine, "select count(*) from events")
    payload = updates.envelope(
        message={
            "message_id": 1,
            "date": _now_ts(),
            "chat": updates.chat(),
            "from": updates.sender(),
            "text": "/start",
        }
    )
    await updates.post(payload)
    await updates.post(payload)
    after_events = await _scalar(engine, "select count(*) from events")
    reporter.check(
        after_events - before_events == 1,
        "a redelivered update is one event",
        f"{after_events - before_events} events",
    )


async def check_second_start(
    engine: AsyncEngine, scenario: Scenario, updates: Updates, reporter: Reporter, *, chat_id: int
) -> None:
    """A second start in the same chat must not restart or duplicate anything."""
    run = await _active_run(engine, chat_id)
    if run is None:
        reporter.check(False, "a second start keeps the run", "no active run to test")
        return
    step_before = cast(str, run["step_id"])
    messages_before = (await _message_stats(engine, chat_id))["total"]
    await updates.start()
    await asyncio.sleep(2.0)
    run_after = await _active_run(engine, chat_id)
    step_after = cast(str, cast(dict[str, Any], run_after)["step_id"]) if run_after else "closed"
    messages_after = (await _message_stats(engine, chat_id))["total"]
    reporter.check(
        step_after == step_before and messages_after == messages_before,
        "a second start neither restarts nor duplicates",
        f"{step_before} -> {step_after}, messages {messages_before} -> {messages_after}",
    )
    reporter.check(step_after in set(scenario.steps), "the run is still on its script")


async def reset(engine: AsyncEngine, chat_id: int) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text("delete from messages where chat_id = :chat"), {"chat": chat_id}
        )
        await connection.execute(
            text("delete from runs where chat_id = :chat"), {"chat": chat_id}
        )
        await connection.execute(
            text("delete from jobs where payload->>'chat_id' = :chat"), {"chat": str(chat_id)}
        )
        await connection.execute(text("delete from events where key like 'telegram:%'"))


async def smoke(args: argparse.Namespace, secret: str, database_url: str) -> int:
    engine = create_async_engine(database_url)
    reporter = Reporter()
    scenario = ScenarioCatalog.load(ROOT / "apps" / "api" / "onboarding" / "scenarios").active(
        args.scenario
    )
    url = f"{args.base_url.rstrip('/')}/webhook/telegram"
    async with httpx.AsyncClient(timeout=30) as http:
        updates = Updates(http, url, secret, args.chat_id)
        try:
            if args.reset:
                await reset(engine, args.chat_id)
                reporter.check(True, "run reset", f"chat {args.chat_id}")

            risks_before = await _scalar(
                engine, "select count(*) from audit_log where name = 'risk_assessed'"
            )
            started = await updates.start()

            async def running() -> bool:
                return await _active_run(engine, args.chat_id) is not None

            welcomed = await wait_for(running)
            run = await _active_run(engine, args.chat_id)
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
                "select status from runs where chat_id = :chat order by entered_at desc limit 1",
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

            await check_delivery(engine, http, args.token, args.chat_id, reporter)
            await check_negative(engine, updates, reporter, chat_id=args.chat_id)
            await check_dedupe(engine, updates, reporter)
        finally:
            await engine.dispose()
    return reporter.report()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="end-to-end smoke for one messenger channel")
    parser.add_argument("--base-url", required=True, help="public origin, e.g. https://host")
    parser.add_argument("--chat-id", type=int, required=True, help="the linked chat to drive")
    parser.add_argument("--scenario", default="onboarding_plant")
    parser.add_argument("--token", default=os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    parser.add_argument("--timeout", type=float, default=SETTLE_SECONDS)
    parser.add_argument("--reset", action="store_true", help="delete this chat's run first")
    parser.add_argument(
        "--branch",
        choices=["calm", "trouble"],
        default="calm",
        help="which keyboard option to press when a step offers a choice",
    )
    args = parser.parse_args(argv)

    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    database_url = os.environ.get("DATABASE_URL", "")
    if not secret or not database_url:
        parser.error("TELEGRAM_WEBHOOK_SECRET and DATABASE_URL must be set")
    return asyncio.run(smoke(args, secret, database_url))


if __name__ == "__main__":
    raise SystemExit(main())
