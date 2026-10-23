"""Cron-compatible tick.

The worker already owns the loop. This module is the deployment shape the client asked for: a
process a scheduler can call every minute, which does a bounded amount of work and exits. It shares
every building block with the worker, so there is no second scheduler to keep correct.

Exit code is 0 when the pass finished, whatever it found. A crash is visible to cron as a non-zero
exit and to the operator as a traceback in the log.
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from onboarding.app.clock import SystemClock
from onboarding.app.container import build_container
from onboarding.app.db.outbox import MessageDispatcher
from onboarding.app.db.scheduler import ReminderScheduler
from onboarding.app.settings import Settings
from onboarding.app.worker.jobs import JobRunner

log = logging.getLogger(__name__)

DEFAULT_MAX_JOBS = 200


async def tick_once(
    *,
    scheduler: ReminderScheduler,
    runner: JobRunner,
    dispatcher: MessageDispatcher,
    max_jobs: int = DEFAULT_MAX_JOBS,
) -> tuple[int, int, int]:
    """Reminders queued, jobs handled, messages delivered."""
    queued = await scheduler.tick()
    handled = 0
    while handled < max_jobs:
        batch = await runner.run_once()
        if batch == 0:
            break
        handled += batch
    delivered = await dispatcher.run_once()
    log.info(
        "cron pass: reminders=%s jobs=%s messages=%s", queued, handled, delivered
    )
    return queued, handled, delivered


async def run(settings: Settings, *, max_jobs: int) -> tuple[int, int, int]:
    container = build_container(settings)
    runner = JobRunner(
        queue=container.queue,
        service=container.service,
        clock=SystemClock(),
        audit=container.audit,
    )
    try:
        return await tick_once(
            scheduler=container.scheduler,
            runner=runner,
            dispatcher=container.dispatcher,
            max_jobs=max_jobs,
        )
    finally:
        await container.aclose()


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    parser = argparse.ArgumentParser(prog="onboarding.app.scheduler")
    parser.add_argument("--max-jobs", type=int, default=DEFAULT_MAX_JOBS)
    args = parser.parse_args(argv)
    asyncio.run(run(Settings(), max_jobs=args.max_jobs))


if __name__ == "__main__":
    main()
