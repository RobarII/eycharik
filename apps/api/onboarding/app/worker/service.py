"""Orchestration: load the run, apply the pure transition, persist, then act.

The order is the guarantee: state and reminder are stored before any message is sent, so a crash
repeats a send at worst and never loses a step.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from math import ceil
from uuid import uuid4

from onboarding.app.audit import NullAudit
from onboarding.app.scenarios import ScenarioCatalog
from onboarding.app.worker.actions import ActionContext, ActionExecutor
from onboarding.core.models import (
    Action,
    ActionKind,
    Address,
    CancelReminder,
    EmployeeId,
    Event,
    EventKind,
    Question,
    RiskSignal,
    RunId,
    Scenario,
    ScheduledEntry,
    Step,
    StepKind,
    StepState,
    SurveyAnswer,
    Transition,
)
from onboarding.core.risk import assess, keyword_signal, scale_signal
from onboarding.core.transitions import (
    advance,
    asks_about_stage,
    has_words,
    is_confirmation,
    is_question,
    jump,
    replay,
    resume_scheduled,
    start,
)
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

    async def start(self, employee_id: EmployeeId, address: Address) -> ServiceResult:
        stored = await self._runs.find_active_by_employee(employee_id)
        if stored is not None:
            # A start never resets progress: it asks the same question again, so a person who lost
            # the message (or cleared the chat) can get the keyboard back. A start from another
            # messenger also moves the address, because the run follows the person (ADR 0019).
            if stored.address == address:
                await self._audit.record(
                    "run_restarted", employee_id=str(employee_id), step=stored.state.step_id
                )
            return await self._resume(stored, address)

        profile = await self._directory.profile(employee_id)
        if profile is None:
            await self._audit.record("employee_not_in_directory", employee_id=str(employee_id))
            return ServiceResult(handled=False)
        scenario = self._scenario(profile.scenario_id)
        now = self._now()
        transition = start(scenario, RunId(str(uuid4())), employee_id, now)
        try:
            await self._runs.create(
                StoredRun(
                    state=transition.state,
                    reminder=transition.reminder,
                    address=address,
                    scheduled=transition.scheduled,
                )
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
        await self._act(transition.actions, address, employee_id, now.date(), question=None)
        if transition.scheduled is not None:
            await self._ack_scheduled(
                scenario, transition.scheduled, address, employee_id, now.date()
            )
        return ServiceResult(handled=True)

    async def _resume(self, stored: StoredRun, address: Address) -> ServiceResult:
        scenario = self._catalog.get(stored.state.scenario_id, stored.state.scenario_version)
        employee_id = stored.state.employee_id
        now = self._now()
        transition = (
            resume_scheduled(scenario, stored.state, now)
            if stored.scheduled is not None
            else replay(scenario, stored.state, now)
        )
        await self._runs.save(
            StoredRun(
                state=transition.state,
                reminder=transition.reminder,
                address=address,
                active=True,
                scheduled=transition.scheduled,
            )
        )
        if stored.address != address:
            await self._audit.record(
                "channel_changed",
                employee_id=str(employee_id),
                previous_channel=stored.address.channel.value,
                previous_chat_id=int(stored.address.chat_id),
                channel=address.channel.value,
                chat_id=int(address.chat_id),
                resumed=True,
            )
        await self._act(transition.actions, address, employee_id, now.date(), question=None)
        if transition.scheduled is not None:
            await self._ack_scheduled(
                scenario, transition.scheduled, address, employee_id, now.date()
            )
        return ServiceResult(handled=True)

    async def handle(  # noqa: PLR0911, PLR0912 - command routing is explicit here
        self,
        employee_id: EmployeeId,
        address: Address,
        event: Event,
    ) -> ServiceResult:
        now = self._now()
        command = _command(event.text)
        # These two commands must work even before there is an active run: /reboot is what makes a
        # demo account look new again, and /start is still the normal entry point.
        if event.kind is EventKind.MESSAGE_RECEIVED:
            if command == "/reboot":
                return await self.reboot(employee_id, address)
            if command == "/start":
                return await self.start(employee_id, address)

        stored = await self._runs.find_active_by_employee(employee_id)
        if stored is None:
            return await self._after_run(employee_id, address, event, command)

        scenario = self._catalog.get(stored.state.scenario_id, stored.state.scenario_version)
        # Reminders are scheduled from processing time, never from a delivery timestamp: a retried
        # update can be hours old, and a timeout due in the past would escalate immediately.
        if command == "/nextstage":
            return await self.next_stage(employee_id, address)
        if event.kind is EventKind.MESSAGE_RECEIVED and command is not None:
            await self._audit.record(
                "command_handled", employee_id=str(employee_id), command=command
            )
            text = (
                self._executor.help_text()
                if command == "/help"
                else self._executor.unknown_command_text()
            )
            await self._act(
                (Action(kind=ActionKind.SEND, text=text),),
                address,
                employee_id,
                now.date(),
                question=None,
            )
            return ServiceResult(handled=True)
        if event.kind is EventKind.BUTTON_PRESSED and event.button_id == "hr_continue":
            return await self.next_stage(employee_id, address)
        if event.kind is EventKind.BUTTON_PRESSED and _asks_a_question(event.button_id):
            await self._act(
                (Action(kind=ActionKind.SEND, text=self._executor.ask_question_text()),),
                address,
                employee_id,
                now.date(),
                question=None,
            )
            return ServiceResult(handled=True)
        if stored.scheduled is not None:
            # The next stage is waiting for its due time. A free-text question must still reach
            # Answerer/QuestionLog; otherwise the person sees "not yet" and HR never gets a row.
            await self._audit.record(
                "event_while_scheduled",
                employee_id=str(employee_id),
                step=stored.scheduled.step_id,
                event=event.kind.value,
            )
            # A caption is the message: a document with a question is a question, and silence
            # here would swallow it, exactly like a text question in the same state.
            asks_something = (
                event.kind is EventKind.FILE_RECEIVED
                and bool(event.text)
                and is_question(event.text)
            )
            if (
                event.kind is EventKind.MESSAGE_RECEIVED
                and event.text
                and not is_confirmation(event.text)
            ) or asks_something:
                await self._act(
                    (Action(kind=ActionKind.ANSWER),),
                    address,
                    employee_id,
                    now.date(),
                    question=event.text,
                )
                return ServiceResult(handled=True)
            if event.kind is EventKind.FILE_RECEIVED:
                # The file is already stored by the intake job, and the stage notice went out when
                # the step was entered. Repeating it per document is noise (measured 2026-10-24:
                # two identical "next stage" messages in one dialog).
                return ServiceResult(handled=True)
            if event.kind is EventKind.MESSAGE_RECEIVED:
                # "Понятно", "спасибо", "готово" while the stage waits for its due time is not a
                # request for a status: answering each one repeated the same notice (measured live
                # 2026-10-24: six identical "Следующий этап" messages in a row). Only a button
                # press on a stale keyboard is a real question about the stage.
                return ServiceResult(handled=True)
            upcoming = scenario.step(stored.scheduled.step_id)
            if not _button_belongs(upcoming, event.button_id):
                # A press on the keyboard of a step the run has already left is a stale tap. Live
                # 2026-10-24: a double tap on "Всё открывается" sent two identical stage notices.
                return ServiceResult(handled=True)
            await self._ack_scheduled(
                scenario,
                stored.scheduled,
                address,
                employee_id,
                now.date(),
                waiting=True,
            )
            return ServiceResult(handled=True)

        if event.kind is EventKind.MESSAGE_RECEIVED and event.text and not has_words(event.text):
            # An emoji is not a question: it used to be logged and escalated to HR as "no sources".
            await self._act(
                (Action(kind=ActionKind.SEND, text=self._executor.not_understood_text()),),
                address,
                employee_id,
                now.date(),
                question=None,
            )
            return ServiceResult(handled=True)
        if (
            event.kind is EventKind.MESSAGE_RECEIVED
            and event.text
            and asks_about_stage(event.text)
            and scenario.step(stored.state.step_id).kind is StepKind.WAIT
        ):
            # The run knows the current step; repeating it beats "no answer in the knowledge base".
            await self._audit.record("stage_replayed", employee_id=str(employee_id))
            await self._act(
                replay(scenario, stored.state, now).actions,
                address,
                employee_id,
                now.date(),
                question=None,
            )
            return ServiceResult(handled=True)

        event_at = event.at if event.at.tzinfo is not None else event.at.replace(tzinfo=UTC)
        effective = event if event_at >= now else replace(event, at=now)
        transition = advance(scenario, stored.state, effective)
        completed = any(action.kind is ActionKind.COMPLETE for action in transition.actions)
        # The person may answer from any linked messenger. The run follows them: replies and the
        # next reminder go to the address they just used (ADR 0019).
        moved = stored.address != address
        scheduled = transition.scheduled
        if scheduled is None and transition.state.step_id == stored.state.step_id:
            # An idle answer or a repeated question must not cancel a stage that is already
            # waiting for its due time.
            scheduled = stored.scheduled
        await self._runs.save(
            StoredRun(
                state=transition.state,
                reminder=transition.reminder,
                address=address,
                active=not completed,
                scheduled=scheduled,
            )
        )
        if moved:
            await self._audit.record(
                "channel_changed",
                employee_id=str(employee_id),
                previous_channel=stored.address.channel.value,
                previous_chat_id=int(stored.address.chat_id),
                channel=address.channel.value,
                chat_id=int(address.chat_id),
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
        if event.kind is EventKind.FILE_RECEIVED and not (event.text and is_question(event.text)):
            await self._act(
                (Action(kind=ActionKind.SEND, text=self._executor.file_received_text()),),
                address,
                employee_id,
                effective.at.date(),
                question=None,
            )
        await self._act(
            transition.actions,
            address,
            employee_id,
            effective.at.date(),
            question=event.text,
        )
        if scheduled is not None:
            await self._ack_scheduled(
                scenario, scheduled, address, employee_id, effective.at.date()
            )
        return ServiceResult(handled=True, escalated=escalated, completed=completed)

    async def _after_run(
        self,
        employee_id: EmployeeId,
        address: Address,
        event: Event,
        command: str | None,
    ) -> ServiceResult:
        """Work the same way after the scenario ended as during it.

        The completion message promises "я на связи" — live run 2026-10-24 showed the opposite:
        every message after ``done`` was dropped with an ``event_without_run`` audit row, questions
        included. Commands and questions now behave the same before and after completion.
        """
        now = self._now()
        if command is not None and event.kind is EventKind.MESSAGE_RECEIVED:
            text = (
                self._executor.no_next_stage_text()
                if command == "/nextstage"
                else self._executor.help_text()
                if command == "/help"
                else self._executor.unknown_command_text()
            )
            await self._audit.record(
                "command_after_completion", employee_id=str(employee_id), command=command
            )
            await self._act(
                (Action(kind=ActionKind.SEND, text=text),),
                address,
                employee_id,
                now.date(),
                question=None,
            )
            return ServiceResult(handled=True)
        if event.kind is EventKind.BUTTON_PRESSED and event.button_id in _POST_RUN_BUTTONS:
            await self._on_post_run_button(
                event.button_id or "", employee_id, address, now.date()
            )
            return ServiceResult(handled=True)
        asks = (
            event.text
            if event.kind in {EventKind.MESSAGE_RECEIVED, EventKind.FILE_RECEIVED}
            else None
        )
        if asks and has_words(asks) and is_question(asks):
            await self._audit.record("answer_after_completion", employee_id=str(employee_id))
            await self._act(
                (Action(kind=ActionKind.ANSWER),),
                address,
                employee_id,
                now.date(),
                question=asks,
            )
            return ServiceResult(handled=True)
        await self._audit.record("event_without_run", employee_id=str(employee_id))
        return ServiceResult(handled=False)

    async def _on_post_run_button(
        self,
        button_id: str,
        employee_id: EmployeeId,
        address: Address,
        today: date,
    ) -> None:
        """The completion menu: benefits answer, a question for HR, or a fresh run."""
        await self._audit.record(
            "post_run_menu", employee_id=str(employee_id), button=button_id
        )
        if button_id == "post_reboot":
            await self.reboot(employee_id, address)
            return
        if button_id == "post_ask":
            await self._act(
                (Action(kind=ActionKind.SEND, text=self._executor.ask_question_text()),),
                address,
                employee_id,
                today,
                question=None,
            )
            return
        await self._act(
            (Action(kind=ActionKind.ANSWER),),
            address,
            employee_id,
            today,
            question=self._executor.post_run_benefits_text(),
        )

    async def reboot(self, employee_id: EmployeeId, address: Address) -> ServiceResult:
        """Close the current run and make the same person start from the welcome again.

        This is a demo command, not an HR action: it exists so a reviewer can show a clean first
        launch without editing the database. The old run stays in the audit trail as completed.
        """
        stored = await self._runs.find_active_by_employee(employee_id)
        if stored is not None:
            await self._runs.save(
                StoredRun(
                    state=stored.state,
                    reminder=CancelReminder(),
                    address=stored.address,
                    active=False,
                    scheduled=None,
                )
            )
            await self._audit.record("run_rebooted", employee_id=str(employee_id))
        return await self.start(employee_id, address)

    async def next_stage(self, employee_id: EmployeeId, address: Address) -> ServiceResult:
        """Move to the next timeline stage now (demo-only ``/nextStage``)."""
        stored = await self._runs.find_active_by_employee(employee_id)
        if stored is None:
            now = self._now()
            await self._act(
                (Action(kind=ActionKind.SEND, text=self._executor.no_next_stage_text()),),
                address,
                employee_id,
                now.date(),
                question=None,
            )
            return ServiceResult(handled=True)
        scenario = self._catalog.get(stored.state.scenario_id, stored.state.scenario_version)
        target = _next_stage_target(scenario, stored)
        now = self._now()
        if target is None:
            await self._act(
                (Action(kind=ActionKind.SEND, text=self._executor.no_next_stage_text()),),
                address,
                employee_id,
                now.date(),
                question=None,
            )
            return ServiceResult(handled=True)
        transition = jump(scenario, stored.state, target, now)
        completed = any(action.kind is ActionKind.COMPLETE for action in transition.actions)
        await self._runs.save(
            StoredRun(
                state=transition.state,
                reminder=transition.reminder,
                address=address,
                active=not completed,
                scheduled=transition.scheduled,
            )
        )
        await self._audit.record(
            "stage_skipped",
            employee_id=str(employee_id),
            previous_step=stored.state.step_id,
            step=transition.state.step_id,
        )
        await self._act(
            transition.actions,
            address,
            employee_id,
            now.date(),
            question=None,
        )
        if transition.scheduled is not None:
            await self._ack_scheduled(
                scenario, transition.scheduled, address, employee_id, now.date()
            )
        return ServiceResult(handled=True, completed=completed)

    async def resume_scheduled(self, run_id: RunId, step_id: str) -> ServiceResult:
        """Emit a step whose delay elapsed, if the run is still waiting on that exact step."""
        stored = await self._runs.load(run_id)
        if stored is None or not stored.active:
            return ServiceResult(handled=False)
        if stored.state.step_id != step_id:
            await self._audit.record(
                "scheduled_step_stale",
                run_id=str(run_id),
                expected=step_id,
                actual=stored.state.step_id,
            )
            return ServiceResult(handled=False)
        scenario = self._catalog.get(stored.state.scenario_id, stored.state.scenario_version)
        now = self._now()
        transition = resume_scheduled(scenario, stored.state, now)
        completed = any(action.kind is ActionKind.COMPLETE for action in transition.actions)
        await self._runs.save(
            StoredRun(
                state=transition.state,
                reminder=transition.reminder,
                address=stored.address,
                active=not completed,
                scheduled=transition.scheduled,
            )
        )
        await self._audit.record(
            "scheduled_step_sent",
            employee_id=str(stored.state.employee_id),
            step=step_id,
            due=True,
        )
        await self._act(
            transition.actions,
            stored.address,
            stored.state.employee_id,
            now.date(),
            question=None,
        )
        if transition.scheduled is not None:
            await self._ack_scheduled(
                scenario,
                transition.scheduled,
                stored.address,
                stored.state.employee_id,
                now.date(),
            )
        return ServiceResult(handled=True, completed=completed)

    async def _ack_scheduled(
        self,
        scenario: Scenario,
        scheduled: ScheduledEntry,
        address: Address,
        employee_id: EmployeeId,
        on_date: date,
        *,
        waiting: bool = False,
    ) -> None:
        """Tell the person that the next stage is scheduled, not lost."""
        step = scenario.step(scheduled.step_id)
        stage = step.title or step.id
        due = (
            scheduled.due_at
            if scheduled.due_at.tzinfo is not None
            else scheduled.due_at.replace(tzinfo=UTC)
        )
        when = _relative_due(due, self._now())
        text = (
            self._executor.stage_waiting_text(stage, when)
            if waiting
            else self._executor.stage_scheduled_text(stage, when)
        )
        await self._act(
            (Action(kind=ActionKind.SEND, text=text),),
            address,
            employee_id,
            on_date,
            question=None,
        )

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
        address: Address,
        employee_id: EmployeeId,
        on_date: date,
        *,
        question: str | None,
    ) -> None:
        profile = await self._directory.profile(employee_id)
        context = ActionContext(
            address=address,
            on_date=on_date,
            employee_id=employee_id,
            profile=profile,
            question=question,
        )
        for action in actions:
            await self._executor.execute(action, context)


_POST_RUN_BUTTONS = frozenset({"post_benefits", "post_ask", "post_reboot"})


def _asks_a_question(button_id: str | None) -> bool:
    """The "ask a question" button carries a per-step id, so one keyboard cannot repeat another."""
    return button_id == "hr_ask" or bool(button_id and button_id.endswith("_ask"))


def _button_belongs(step: Step, button_id: str | None) -> bool:
    if button_id is None:
        return False
    return any(button.id == button_id for row in step.keyboard for button in row)


def _command(text: str | None) -> str | None:
    """Return a slash command, without the optional ``@bot`` suffix."""
    if not text:
        return None
    token = text.strip().split(maxsplit=1)[0]
    if not token.startswith("/"):
        return None
    return token.split("@", 1)[0].lower()


def _next_stage_target(scenario: Scenario, stored: StoredRun) -> str | None:
    """The next step a demo should show, preferring a real delayed stage boundary."""
    if stored.scheduled is not None:
        return stored.scheduled.step_id
    target = _following_step(scenario.step(stored.state.step_id))
    seen: set[str] = set()
    fallback: str | None = None
    while target is not None and target not in seen:
        seen.add(target)
        step = scenario.step(target)
        if fallback is None:
            fallback = target
        if step.delay is not None or step.kind in {"wait", "survey", "terminal"}:
            return target
        target = _following_step(step)
    return fallback


def _relative_due(due: datetime, now: datetime) -> str:
    """Say when the next stage is due in human time, never as a UTC timestamp.

    An absolute ``18:30 UTC`` looks like the past to a person whose clock says ``21:30``. Relative
    wording is also truthful when the worker is a little late: a due point that has just passed
    becomes ``сейчас`` instead of a date the reader has to interpret.
    """
    seconds = (due - now).total_seconds()
    if seconds <= 0:
        return "сейчас"
    minutes = max(1, ceil(seconds / 60))
    if minutes < 60:
        return f"через {minutes} {_plural(minutes, 'минуту', 'минуты', 'минут')}"
    hours = max(1, ceil(seconds / 3600))
    if hours < 24:
        return f"через {hours} {_plural(hours, 'час', 'часа', 'часов')}"
    days = max(1, ceil(seconds / 86400))
    return f"через {days} {_plural(days, 'день', 'дня', 'дней')}"


def _plural(value: int, one: str, few: str, many: str) -> str:
    last_two = value % 100
    if 11 <= last_two <= 14:
        return many
    last = value % 10
    if last == 1:
        return one
    if 2 <= last <= 4:
        return few
    return many


def _following_step(step: object) -> str | None:
    next_step = getattr(step, "next_step", None)
    if next_step is not None:
        return str(next_step)
    routes = getattr(step, "routes", {})
    if not routes:
        return None
    for key in ("default", "ready", "access_ok", "tone_formal", "tone_you", "done", "yes"):
        if key in routes:
            return str(routes[key])
    return str(next(iter(routes.values())))
