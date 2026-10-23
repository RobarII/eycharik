"""Orchestration: load the run, apply the pure transition, persist, then act.

The order is the guarantee: state and reminder are stored before any message is sent, so a crash
repeats a send at worst and never loses a step.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from uuid import uuid4

from onboarding.app.audit import NullAudit
from onboarding.app.scenarios import ScenarioCatalog
from onboarding.app.worker.actions import ActionContext, ActionExecutor
from onboarding.core.models import (
    Action,
    ActionKind,
    ChatId,
    EmployeeId,
    Event,
    Question,
    RiskSignal,
    RunId,
    Scenario,
    StepState,
    SurveyAnswer,
    Transition,
)
from onboarding.core.risk import assess, keyword_signal, scale_signal
from onboarding.core.transitions import advance, start
from onboarding.ports import (
    AuditLog,
    Clock,
    Directory,
    RunAlreadyActiveError,
    RunRepository,
    SentimentAnalysis,
    StoredRun,
)


@dataclass(frozen=True, slots=True)
class ServiceResult:
    handled: bool
    escalated: bool = False
    completed: bool = False


class OnboardingService:
    def __init__(
        self,
        *,
        runs: RunRepository,
        catalog: ScenarioCatalog,
        executor: ActionExecutor,
        clock: Clock,
        directory: Directory,
        audit: AuditLog | None = None,
        classifier: SentimentAnalysis | None = None,
        scenario_id: str = "onboarding_default",
        scenario_version: int | None = None,
    ) -> None:
        self._runs = runs
        self._catalog = catalog
        self._executor = executor
        self._clock = clock
        self._directory = directory
        self._audit = audit or NullAudit()
        self._classifier = classifier
        self._scenario_id = scenario_id
        self._scenario_version = scenario_version

    def _scenario(self, scenario_id: str | None = None) -> Scenario:
        chosen = scenario_id or self._scenario_id
        if self._scenario_version is not None:
            return self._catalog.get(chosen, self._scenario_version)
        return self._catalog.active(chosen)

    async def start(self, employee_id: EmployeeId, chat_id: ChatId) -> ServiceResult:
        if await self._runs.find_active_by_employee(employee_id) is not None:
            await self._audit.record("run_already_active", employee_id=str(employee_id))
            return ServiceResult(handled=False)

        profile = await self._directory.profile(employee_id)
        if profile is None:
            await self._audit.record("employee_not_in_directory", employee_id=str(employee_id))
            return ServiceResult(handled=False)
        scenario = self._scenario(profile.scenario_id)
        now = self._now()
        transition = start(scenario, RunId(str(uuid4())), employee_id, now)
        try:
            await self._runs.create(
                StoredRun(state=transition.state, reminder=transition.reminder, chat_id=chat_id)
            )
        except RunAlreadyActiveError:
            await self._audit.record("run_creation_raced", employee_id=str(employee_id))
            return ServiceResult(handled=False)
        await self._audit.record(
            "run_started",
            employee_id=str(employee_id),
            scenario=scenario.id,
            version=scenario.version,
        )
        await self._act(transition.actions, chat_id, employee_id, now.date(), question=None)
        return ServiceResult(handled=True)

    async def handle(
        self,
        employee_id: EmployeeId,
        chat_id: ChatId,
        event: Event,
    ) -> ServiceResult:
        stored = await self._runs.find_active_by_employee(employee_id)
        if stored is None:
            await self._audit.record("event_without_run", employee_id=str(employee_id))
            return ServiceResult(handled=False)

        scenario = self._catalog.get(stored.state.scenario_id, stored.state.scenario_version)
        # Reminders are scheduled from processing time, never from a delivery timestamp: a retried
        # update can be hours old, and a timeout due in the past would escalate immediately.
        now = self._now()
        event_at = event.at if event.at.tzinfo is not None else event.at.replace(tzinfo=UTC)
        effective = event if event_at >= now else replace(event, at=now)
        transition = advance(scenario, stored.state, effective)
        completed = any(action.kind is ActionKind.COMPLETE for action in transition.actions)
        await self._runs.save(
            StoredRun(
                state=transition.state,
                reminder=transition.reminder,
                chat_id=stored.chat_id,
                active=not completed,
            )
        )
        await self._audit.record(
            "step_transition",
            employee_id=str(employee_id),
            scenario=scenario.id,
            version=scenario.version,
            previous_step=stored.state.step_id,
            step=transition.state.step_id,
            event=event.kind.value,
        )
        escalated = await self._assess_survey(
            scenario, stored.state, transition, employee_id
        )
        await self._act(
            transition.actions,
            stored.chat_id,
            employee_id,
            effective.at.date(),
            question=event.text,
        )
        return ServiceResult(handled=True, escalated=escalated, completed=completed)

    async def _assess_survey(
        self,
        scenario: Scenario,
        previous: StepState,
        transition: Transition,
        employee_id: EmployeeId,
    ) -> bool:
        """Score the answers added by this event and audit the risk they carry."""
        step = scenario.step(previous.step_id)
        if not step.questions:
            return False
        fresh = transition.state.answers[len(previous.answers) :]
        if not fresh:
            return False
        signals = await self._signals(step.questions, fresh)
        assessment = assess(signals)
        await self._audit.record(
            "risk_assessed",
            employee_id=str(employee_id),
            run_id=str(previous.run_id),
            step=step.id,
            step_title=step.title,
            level=assessment.level.value,
            score=assessment.score,
            tags=[tag.value for tag in assessment.tags],
            reasons=list(assessment.reasons),
            evidence=[
                {
                    "source": signal.source,
                    "text": signal.text[:500],
                    "sentiment": signal.sentiment.value,
                    "tags": [tag.value for tag in signal.tags],
                    "confidence": signal.confidence,
                }
                for signal in signals[:3]
                if signal.text
            ],
        )
        if assessment.escalate_to is None:
            return False
        await self._audit.record(
            "risk_escalated",
            employee_id=str(employee_id),
            step=step.id,
            to=assessment.escalate_to,
            level=assessment.level.value,
        )
        return True

    async def _signals(
        self, questions: tuple[Question, ...], answers: tuple[SurveyAnswer, ...]
    ) -> tuple[RiskSignal, ...]:
        """Turn stored answers into the one shape the risk rules understand."""
        by_id = {question.id: question for question in questions}
        signals: list[RiskSignal] = []
        for answer in answers:
            question = by_id.get(answer.question_id)
            if question is None:
                continue
            source = f"survey:{answer.question_id}"
            scale = scale_signal(question, answer, source=source)
            if scale is not None:
                signals.append(scale)
            if not answer.text:
                continue
            if self._classifier is not None:
                signals.append(await self._classifier.classify(answer.text, source=source))
            else:
                signals.append(keyword_signal(answer.text, source=source))
        return tuple(signals)

    def _now(self) -> datetime:
        now = self._clock.now()
        return now.replace(tzinfo=UTC) if now.tzinfo is None else now

    async def _act(
        self,
        actions: tuple[Action, ...],
        chat_id: ChatId,
        employee_id: EmployeeId,
        on_date: date,
        *,
        question: str | None,
    ) -> None:
        profile = await self._directory.profile(employee_id)
        context = ActionContext(
            chat_id=chat_id,
            on_date=on_date,
            employee_id=employee_id,
            profile=profile,
            question=question,
        )
        for action in actions:
            await self._executor.execute(action, context)
