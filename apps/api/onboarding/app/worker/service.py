"""Orchestration: load the run, apply the pure transition, persist, then act.

The order is the guarantee: state and reminder are stored before any message is sent, so a crash
repeats a send at worst and never loses a step.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
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
    RunId,
)
from onboarding.core.transitions import advance, start
from onboarding.ports import (
    AuditLog,
    Clock,
    Directory,
    RunAlreadyActiveError,
    RunRepository,
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
        scenario_id: str = "onboarding_default",
    ) -> None:
        self._runs = runs
        self._catalog = catalog
        self._executor = executor
        self._clock = clock
        self._directory = directory
        self._audit = audit or NullAudit()
        self._scenario_id = scenario_id

    async def start(self, employee_id: EmployeeId, chat_id: ChatId) -> ServiceResult:
        if await self._runs.find_active_by_employee(employee_id) is not None:
            await self._audit.record("run_already_active", employee_id=str(employee_id))
            return ServiceResult(handled=False)

        scenario = self._catalog.active(self._scenario_id)
        now = self._clock.now()
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
        transition = advance(scenario, stored.state, event)
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
        await self._act(
            transition.actions,
            stored.chat_id,
            employee_id,
            event.at.date(),
            question=event.text,
        )
        return ServiceResult(handled=True, completed=completed)

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
            profile=profile,
            question=question,
        )
        for action in actions:
            await self._executor.execute(action, context)
