"""Send pacing: a global rate for one bot, and optionally one rate per conversation.

Messengers publish the rule; the channel profile carries it (ADR 0019). Pacing lives next to the
adapter because it is a property of the wire, not of a scenario. The dispatcher delivers one
channel's rows in order, so a simple monotonic wait is enough; the lock keeps two coroutines from
racing on the same timestamp.
"""

from __future__ import annotations

import asyncio
import time


class Pacer:
    def __init__(self, *, per_second: float, per_chat_per_second: float | None) -> None:
        if per_second <= 0:
            raise ValueError("per_second must be positive")
        if per_chat_per_second is not None and per_chat_per_second <= 0:
            raise ValueError("per_chat_per_second must be positive")
        self._global_interval = 1.0 / per_second
        self._chat_interval = (
            None if per_chat_per_second is None else 1.0 / per_chat_per_second
        )
        self._lock = asyncio.Lock()
        self._last_global = 0.0
        self._last_per_chat: dict[int, float] = {}

    async def wait(self, chat_id: int) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._global_interval - (now - self._last_global)
            if self._chat_interval is not None:
                last = self._last_per_chat.get(chat_id, 0.0)
                wait = max(wait, self._chat_interval - (now - last))
            if wait > 0:
                await asyncio.sleep(wait)
                now = time.monotonic()
            self._last_global = now
            if self._chat_interval is not None:
                self._last_per_chat[chat_id] = now
