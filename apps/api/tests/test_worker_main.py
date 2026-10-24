"""The worker loop: one pass of work, a reminder tick, a purge, a clean shutdown.

The loop is long-running by nature, which is why the test owns the stop event and the clock: it
runs exactly as many iterations as the test asks for, then proves that the container was closed on
the way out — a process that leaks its database on SIGTERM is a deployment that needs a restart.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import pytest

from onboarding.app.worker import main as worker


@dataclass
class StopAfter:
    """A runner that stops the loop after a fixed number of passes."""

    passes: int
    stop: object
    handled: int = 0
    calls: int = 0

    async def run_once(self) -> int:
        self.calls += 1
        self.handled += 1
        if self.calls >= self.passes:
            self.stop.set()  # type: ignore[attr-defined]
        return 1


@dataclass
class CountingDispatcher:
    calls: int = 0

    async def run_once(self) -> int:
        self.calls += 1
        return 0


@dataclass
class CountingScheduler:
    ticks: int = 0

    async def tick(self) -> int:
        self.ticks += 1
        return 0


@dataclass
class CountingPurger:
    calls: int = 0

    async def run_once(self) -> object:
        self.calls += 1
        return "purged"


@dataclass
class FakeContainer:
    stop: object
    passes: int
    closed: int = 0
    queue: object = field(default_factory=object)
    service: object = field(default_factory=object)
    clock: object = field(default_factory=object)
    audit: object = field(default_factory=object)
    extractor: object = field(default_factory=object)
    indexer: object = field(default_factory=object)
    files: object = field(default_factory=object)
    database: object = field(default_factory=object)
    dispatcher: CountingDispatcher = field(default_factory=CountingDispatcher)
    scheduler: CountingScheduler = field(default_factory=CountingScheduler)

    async def aclose(self) -> None:
        self.closed += 1


async def test_the_loop_runs_until_the_stop_event_and_closes_the_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stop = asyncio.Event()
    container = FakeContainer(stop=stop, passes=2)
    runner = StopAfter(passes=2, stop=stop)
    purger = CountingPurger()

    monkeypatch.setattr(worker, "build_container", lambda settings: container)
    monkeypatch.setattr(worker, "JobRunner", lambda **kwargs: runner)
    monkeypatch.setattr(worker, "RetentionPurger", lambda *args, **kwargs: purger)
    # The purge is hourly; a test may not wait an hour to prove it runs.
    monkeypatch.setattr(worker, "RETENTION_EVERY_S", 0.0)
    monkeypatch.setattr(worker, "IDLE_SLEEP_S", 0.0)

    await worker.run_forever(worker.Settings(_env_file=None), stop)

    assert stop.is_set()
    assert container.closed == 1
    assert runner.calls == 2
    assert purger.calls == 2
    # A reminder tick happens on the first pass, not on every one.
    assert container.scheduler.ticks == 1
    assert container.dispatcher.calls == 2


def test_main_installs_a_signal_handler_and_runs_the_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[object, object]] = []

    async def fake_run_forever(settings: object, stop: object) -> None:
        seen.append((settings, stop))

    monkeypatch.setattr(worker, "run_forever", fake_run_forever)

    worker.main()

    assert len(seen) == 1
    settings, stop = seen[0]
    assert isinstance(settings, worker.Settings)
    assert stop is not None
