"""The cron entry point is the deployment shape the client asked for.

It shares every building block with the worker, so the only thing worth testing here is the wiring:
the pass is bounded, the purge is optional, and the exit path closes the container.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from onboarding.app.scheduler import main as cron


@dataclass
class CountingScheduler:
    ticks: int = 0

    async def tick(self) -> int:
        self.ticks += 1
        return 2


@dataclass
class ScriptedRunner:
    batches: list[int] = field(default_factory=list)
    calls: int = 0

    async def run_once(self) -> int:
        self.calls += 1
        return self.batches.pop(0) if self.batches else 0


@dataclass
class CountingDispatcher:
    calls: int = 0

    async def run_once(self) -> int:
        self.calls += 1
        return 3


@dataclass
class CountingPurger:
    calls: int = 0

    async def run_once(self) -> object:
        self.calls += 1
        return "purged"


async def test_a_pass_queues_reminders_drains_jobs_and_delivers() -> None:
    scheduler = CountingScheduler()
    runner = ScriptedRunner(batches=[4, 1])
    dispatcher = CountingDispatcher()
    purger = CountingPurger()

    result = await cron.tick_once(
        scheduler=scheduler,  # type: ignore[arg-type]
        runner=runner,  # type: ignore[arg-type]
        dispatcher=dispatcher,  # type: ignore[arg-type]
        purger=purger,  # type: ignore[arg-type]
        max_jobs=100,
    )

    assert result == (2, 5, 3)
    assert scheduler.ticks == 1
    assert runner.calls == 3  # two batches, then the empty one that ends the pass
    assert dispatcher.calls == 1
    assert purger.calls == 1


async def test_a_pass_stops_at_the_job_budget() -> None:
    """A cron pass has to finish before the next minute, even when the queue is endless."""
    runner = ScriptedRunner(batches=[10, 10, 10])

    queued, handled, _ = await cron.tick_once(
        scheduler=CountingScheduler(),  # type: ignore[arg-type]
        runner=runner,  # type: ignore[arg-type]
        dispatcher=CountingDispatcher(),  # type: ignore[arg-type]
        max_jobs=10,
    )

    assert (queued, handled) == (2, 10)
    assert runner.calls == 1


async def test_the_purge_is_optional() -> None:
    _, _, _ = await cron.tick_once(
        scheduler=CountingScheduler(),  # type: ignore[arg-type]
        runner=ScriptedRunner(),
        dispatcher=CountingDispatcher(),  # type: ignore[arg-type]
    )


def test_the_command_line_carries_the_job_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[int] = []

    async def fake_run(settings: object, *, max_jobs: int) -> tuple[int, int, int]:
        del settings
        seen.append(max_jobs)
        return (0, 0, 0)

    monkeypatch.setattr(cron, "run", fake_run)

    cron.main([])
    cron.main(["--max-jobs", "7"])

    assert seen == [cron.DEFAULT_MAX_JOBS, 7]


async def test_run_builds_the_graph_and_closes_it(monkeypatch: pytest.MonkeyPatch) -> None:
    @dataclass
    class FakeContainer:
        scheduler: CountingScheduler = field(default_factory=CountingScheduler)
        dispatcher: CountingDispatcher = field(default_factory=CountingDispatcher)
        closed: int = 0
        queue: object = field(default_factory=object)
        service: object = field(default_factory=object)
        clock: object = field(default_factory=object)
        audit: object = field(default_factory=object)
        extractor: object = field(default_factory=object)
        indexer: object = field(default_factory=object)
        database: object = field(default_factory=object)

        async def aclose(self) -> None:
            self.closed += 1

    container = FakeContainer()
    monkeypatch.setattr(cron, "build_container", lambda settings: container)
    monkeypatch.setattr(
        cron,
        "JobRunner",
        lambda **kwargs: ScriptedRunner(batches=[1]),
    )
    monkeypatch.setattr(
        cron,
        "RetentionPurger",
        lambda *args, **kwargs: CountingPurger(),
    )

    queued, handled, delivered = await cron.run(cron.Settings(_env_file=None), max_jobs=10)

    assert (queued, handled, delivered) == (2, 1, 3)
    assert container.closed == 1
