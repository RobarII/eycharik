from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from onboarding.app.clock import FrozenClock
from onboarding.app.copy import load_copy
from onboarding.app.scenarios import ScenarioCatalog, ScenarioCatalogError
from onboarding.app.worker.actions import ActionExecutor
from onboarding.app.worker.service import OnboardingService
from onboarding.core.models import (
    ChatId,
    EmployeeId,
    Event,
    EventKind,
    ScheduleReminder,
)
from onboarding.ports import StoredRun

from .fakes import (
    EMPLOYEE,
    NOW,
    InMemoryRuns,
    RecordingAudit,
    RecordingMessaging,
    StaticDirectory,
    profile,
    stored_run,
)
from .test_actions import StubAnswerer

ROOT = Path(__file__).resolve().parents[3]
SCENARIOS = ROOT / "apps" / "api" / "onboarding" / "scenarios"
COPY = load_copy(ROOT / "docs" / "product" / "copy.yaml")


def build() -> tuple[
    OnboardingService,
    InMemoryRuns,
    RecordingMessaging,
    RecordingAudit,
    StubAnswerer,
]:
    runs = InMemoryRuns()
    messaging = RecordingMessaging()
    audit = RecordingAudit()
    answerer = StubAnswerer()
    executor = ActionExecutor(
        messaging=messaging,
        answerer=answerer,  # type: ignore[arg-type]
        copy=COPY,
        audit=audit,
    )
    service = OnboardingService(
        runs=runs,
        catalog=ScenarioCatalog.load(SCENARIOS),
        executor=executor,
        clock=FrozenClock(NOW),
        directory=StaticDirectory({EMPLOYEE: profile()}),
        audit=audit,
    )
    return service, runs, messaging, audit, answerer


async def test_start_creates_a_run_and_sends_the_first_messages() -> None:
    service, runs, messaging, audit, _ = build()

    result = await service.start(EMPLOYEE, ChatId(1))

    assert result.handled
    assert len(runs.runs) == 1
    assert [message.text for message in messaging.sent] == [
        "Добро пожаловать в «Группу ПОЛИПЛАСТИК»! Я помогу пройти адаптацию: подскажу шаги, "
        "напомню о документах и отвечу на вопросы о компании.",
        "Первый день: получите пропуск и ноутбук, познакомьтесь с наставником, проверьте "
        "доступы. Отметьте, когда всё будет готово.",
    ]
    stored = next(iter(runs.runs.values()))
    assert stored.state.step_id == "first_day_checklist"
    assert isinstance(stored.reminder, ScheduleReminder)
    assert "run_started" in audit.names()


async def test_start_is_idempotent() -> None:
    service, _, messaging, audit, _ = build()

    await service.start(EMPLOYEE, ChatId(1))
    sent_before = len(messaging.sent)
    result = await service.start(EMPLOYEE, ChatId(1))

    assert not result.handled
    assert len(messaging.sent) == sent_before
    assert "run_already_active" in audit.names()


async def test_button_advances_the_run() -> None:
    service, runs, messaging, _, _ = build()
    await service.start(EMPLOYEE, ChatId(1))

    result = await service.handle(
        EMPLOYEE,
        ChatId(1),
        Event(kind=EventKind.BUTTON_PRESSED, at=NOW, button_id="checklist_done"),
    )

    stored = next(iter(runs.runs.values()))
    assert result.handled
    assert stored.state.step_id == "meet_the_team"
    assert messaging.sent[-1].text.startswith("Наставник и руководитель")


async def test_completion_message_is_sent_at_the_terminal_step() -> None:
    service, runs, messaging, _, _ = build()
    await start_at(service, runs, "week_one_check")

    result = await service.handle(
        EMPLOYEE,
        ChatId(1),
        Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="Всё понятно"),
    )

    assert result.completed
    assert messaging.sent[-1].text == COPY.completion


async def test_unknown_employee_is_ignored() -> None:
    service, _, messaging, audit, _ = build()

    result = await service.handle(
        EmployeeId("stranger"),
        ChatId(1),
        Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="привет"),
    )

    assert not result.handled
    assert messaging.sent == []
    assert "event_without_run" in audit.names()


async def test_free_text_at_a_button_step_goes_to_the_assistant() -> None:
    service, runs, messaging, _, answerer = build()
    await service.start(EMPLOYEE, ChatId(1))

    await service.handle(
        EMPLOYEE,
        ChatId(1),
        Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="Сколько дней отпуска?"),
    )

    assert answerer.calls == [("Сколько дней отпуска?", NOW.date())]
    assert messaging.sent[-1].text == "Ответ ассистента"
    stored = next(iter(runs.runs.values()))
    assert stored.state.step_id == "first_day_checklist"


async def start_at(service: OnboardingService, runs: InMemoryRuns, step_id: str) -> None:
    await runs.create(stored_run(step_id=step_id))


def test_catalog_fails_on_a_broken_file(tmp_path: Path) -> None:
    (tmp_path / "bad.yaml").write_text("id: broken\n", encoding="utf-8")

    with pytest.raises(ScenarioCatalogError):
        ScenarioCatalog.load(tmp_path)


def test_catalog_fails_on_a_duplicate_version(tmp_path: Path) -> None:
    source = (SCENARIOS / "onboarding_default.yaml").read_text(encoding="utf-8")
    (tmp_path / "a.yaml").write_text(source, encoding="utf-8")
    (tmp_path / "b.yaml").write_text(source, encoding="utf-8")

    with pytest.raises(ScenarioCatalogError, match="duplicate"):
        ScenarioCatalog.load(tmp_path)


def test_catalog_lists_ids() -> None:
    catalog = ScenarioCatalog.load(SCENARIOS)

    assert catalog.ids() == ("onboarding_default",)
    assert catalog.active("onboarding_default").version == 1


def test_stored_run_helper_matches_the_scenario() -> None:
    run: StoredRun = stored_run(step_id="documents")

    assert run.state.scenario_id == "onboarding_default"
    assert run.state.entered_at.date() == date(2026, 10, 20)
