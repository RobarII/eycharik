from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
import yaml

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
    RiskSignal,
    ScheduleReminder,
    Sentiment,
    SignalTag,
    Tone,
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


def build(*, scenario_id: str = "onboarding_default") -> tuple[
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
        directory=StaticDirectory({EMPLOYEE: profile(scenario_id=scenario_id)}),
        audit=audit,
    )
    return service, runs, messaging, audit, answerer


async def test_start_creates_a_run_and_sends_the_first_messages() -> None:
    service, runs, messaging, audit, _ = build()

    result = await service.start(EMPLOYEE, ChatId(1))

    assert result.handled
    assert len(runs.runs) == 1
    assert len(messaging.sent) == 1
    assert messaging.sent[0].text.startswith("Здравствуйте! Меня зовут Корсик")
    assert messaging.sent[0].keyboard[0][0].id == "tone_you"
    stored = next(iter(runs.runs.values()))
    assert stored.state.step_id == "welcome"
    assert isinstance(stored.reminder, ScheduleReminder)
    assert "run_started" in audit.names()


async def test_start_uses_the_scenario_named_by_the_directory() -> None:
    service, runs, _, audit, _ = build(scenario_id="onboarding_plant")

    result = await service.start(EMPLOYEE, ChatId(1))

    assert result.handled
    stored = next(iter(runs.runs.values()))
    assert stored.state.scenario_id == "onboarding_plant"
    assert stored.state.scenario_version == 1
    assert audit.events[0][1]["scenario"] == "onboarding_plant"


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
        Event(kind=EventKind.BUTTON_PRESSED, at=NOW, button_id="tone_formal"),
    )

    stored = next(iter(runs.runs.values()))
    assert result.handled
    assert stored.state.step_id == "documents_checklist"
    assert messaging.sent[-1].text.startswith("До первого рабочего дня")


async def test_choosing_informal_tone_changes_the_next_message() -> None:
    service, runs, messaging, _, _ = build()
    await service.start(EMPLOYEE, ChatId(1))

    await service.handle(
        EMPLOYEE,
        ChatId(1),
        Event(kind=EventKind.BUTTON_PRESSED, at=NOW, button_id="tone_you"),
    )

    stored = next(iter(runs.runs.values()))
    assert stored.state.tone is Tone.INFORMAL
    assert messaging.sent[-1].text.startswith("Осталось собрать документы")


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
    assert stored.state.step_id == "welcome"


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

    assert catalog.ids() == ("onboarding_default", "onboarding_plant")
    assert catalog.active("onboarding_default").version == 2


def test_stored_run_helper_matches_the_scenario() -> None:
    run: StoredRun = stored_run(step_id="documents")

    assert run.state.scenario_id == "onboarding_default"
    assert run.state.entered_at.date() == date(2026, 10, 20)


async def test_a_stale_delivery_schedules_reminders_from_processing_time() -> None:
    service, runs, _, _, _ = build()
    await service.start(EMPLOYEE, ChatId(1))

    await service.handle(
        EMPLOYEE,
        ChatId(1),
        Event(
            kind=EventKind.BUTTON_PRESSED,
            at=NOW - timedelta(days=2),
            button_id="tone_formal",
        ),
    )

    stored = next(iter(runs.runs.values()))
    assert isinstance(stored.reminder, ScheduleReminder)
    assert stored.reminder.due_at == NOW + timedelta(hours=48)


async def test_a_naive_delivery_timestamp_does_not_crash() -> None:
    service, runs, _, _, _ = build()
    await service.start(EMPLOYEE, ChatId(1))

    await service.handle(
        EMPLOYEE,
        ChatId(1),
        Event(
            kind=EventKind.BUTTON_PRESSED,
            at=datetime(2026, 10, 20, 9, 0),  # noqa: DTZ001 - exercising a naive payload
            button_id="tone_formal",
        ),
    )

    stored = next(iter(runs.runs.values()))
    assert stored.state.step_id == "documents_checklist"


class RecordingClassifier:
    def __init__(self, sentiment: Sentiment, tags: tuple[SignalTag, ...]) -> None:
        self.sentiment = sentiment
        self.tags = tags
        self.calls: list[tuple[str, str]] = []

    async def classify(self, text: str, *, source: str) -> RiskSignal:
        self.calls.append((text, source))
        return RiskSignal(
            source=source, sentiment=self.sentiment, tags=self.tags, confidence=0.9, text=text
        )


def _build_survey(
    tmp_path: Path,
    classifier: object | None = None,
) -> tuple[OnboardingService, InMemoryRuns, RecordingAudit]:
    document = {
        "id": "survey_demo",
        "version": 1,
        "title": "Опрос",
        "start": "check",
        "steps": [
            {
                "id": "check",
                "kind": "survey",
                "message": "Пара вопросов",
                "questions": [
                    {
                        "id": "manager_available",
                        "kind": "scale",
                        "prompt": "Насколько доступен руководитель?",
                        "low_threshold": 8,
                        "reason_prompt": "Что мешает?",
                    }
                ],
                "next": "done",
                "timeout": {"after_hours": 24, "action": "remind"},
            },
            {"id": "done", "kind": "terminal", "outcome": "completed"},
        ],
    }
    (tmp_path / "survey_demo.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
    runs = InMemoryRuns()
    audit = RecordingAudit()
    executor = ActionExecutor(
        messaging=RecordingMessaging(),
        answerer=StubAnswerer(),  # type: ignore[arg-type]
        copy=COPY,
        audit=audit,
    )
    service = OnboardingService(
        runs=runs,
        catalog=ScenarioCatalog.load(tmp_path),
        executor=executor,
        clock=FrozenClock(NOW),
        directory=StaticDirectory({EMPLOYEE: profile(scenario_id="survey_demo")}),
        audit=audit,
        classifier=classifier,  # type: ignore[arg-type]
        scenario_id="survey_demo",
    )
    return service, runs, audit


async def test_survey_answer_is_scored_without_escalating_on_a_score_alone(
    tmp_path: Path,
) -> None:
    service, _, audit = _build_survey(tmp_path)
    await service.start(EMPLOYEE, ChatId(1))

    result = await service.handle(
        EMPLOYEE, ChatId(1), Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="3")
    )

    assert not result.escalated
    risk = next(fields for name, fields in audit.events if name == "risk_assessed")
    assert risk["level"] == "medium"
    assert risk["score"] == 2


async def test_angry_reason_escalates_the_survey(tmp_path: Path) -> None:
    service, _, audit = _build_survey(tmp_path)
    await service.start(EMPLOYEE, ChatId(1))
    await service.handle(
        EMPLOYEE, ChatId(1), Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="3")
    )

    result = await service.handle(
        EMPLOYEE,
        ChatId(1),
        Event(
            kind=EventKind.MESSAGE_RECEIVED,
            at=NOW,
            text="Руководитель не отвечает, конфликт в команде",
        ),
    )

    assert result.escalated
    escalated = next(fields for name, fields in audit.events if name == "risk_escalated")
    assert escalated["to"] == "recruiter"


async def test_the_classifier_labels_free_text_answers(tmp_path: Path) -> None:
    labeler = RecordingClassifier(Sentiment.NEGATIVE, (SignalTag.MANAGER,))
    service, _, audit = _build_survey(tmp_path, labeler)
    await service.start(EMPLOYEE, ChatId(1))
    await service.handle(
        EMPLOYEE, ChatId(1), Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="3")
    )

    result = await service.handle(
        EMPLOYEE,
        ChatId(1),
        Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="Нормально, но руководитель занят"),
    )

    assert labeler.calls == [("Нормально, но руководитель занят", "survey:manager_available")]
    assert result.escalated
    escalated = next(fields for name, fields in audit.events if name == "risk_escalated")
    assert escalated["to"] == "recruiter"
