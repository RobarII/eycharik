"""Worker process: claim jobs, dispatch messages, tick reminders.

One loop, one process. Scaling out means running more copies; ``SKIP LOCKED`` keeps them apart.
"""

from __future__ import annotations

import asyncio
import logging
import signal

from onboarding.app.clock import SystemClock
from onboarding.app.container import build_container
from onboarding.app.db.retention import RetentionPurger
from onboarding.app.settings import Settings
from onboarding.app.worker.jobs import JobRunner

log = logging.getLogger(__name__)

IDLE_SLEEP_S = 0.2
SCHEDULER_EVERY_TICKS = 25
RETENTION_EVERY_S = 60 * 60


async def run_forever(settings: Settings, stop: asyncio.Event) -> None:
    container = build_container(settings)
    runner = JobRunner(
        queue=container.queue,
        service=container.service,
        clock=SystemClock(),
        audit=container.audit,
        extractor=container.extractor,
    )
    purger = RetentionPurger(
        container.database,
        SystemClock(),
        days=settings.data_retention_days,
    )
    ticks = 0
    next_purge = asyncio.get_running_loop().time() + RETENTION_EVERY_S
    try:
        while not stop.is_set():
            handled = await runner.run_once()
            await container.dispatcher.run_once()
            if ticks % SCHEDULER_EVERY_TICKS == 0:
                await container.scheduler.tick()
            if asyncio.get_running_loop().time() >= next_purge:
                await purger.run_once()
                next_purge = asyncio.get_running_loop().time() + RETENTION_EVERY_S
            ticks += 1
            if handled == 0:
                await asyncio.sleep(IDLE_SLEEP_S)
    finally:
        await container.aclose()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = Settings()
    stop = asyncio.Event()

    async def runner() -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop.set)
        await run_forever(settings, stop)

    asyncio.run(runner())


if __name__ == "__main__":
    main()
