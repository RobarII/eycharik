"""Failed-authentication throttling.

A static bearer token is still a secret; without a limit an attacker can guess one for months. The
limiter keeps a sliding window of failures per peer and blocks that peer for a cooldown. It is
in-process on purpose, like the MAX pacing state: one API replica owns its own counters, and a
restart clears them.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(slots=True)
class _Bucket:
    failures: list[float] = field(default_factory=list)
    blocked_until: float = 0.0


class AuthFailureLimiter:
    def __init__(
        self,
        *,
        max_failures: int = 10,
        window_s: float = 60.0,
        block_s: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_failures < 1:
            raise ValueError("max_failures must be at least 1")
        self._max_failures = max_failures
        self._window_s = window_s
        self._block_s = block_s
        self._clock = clock
        self._buckets: dict[str, _Bucket] = {}

    def blocked(self, key: str) -> bool:
        bucket = self._buckets.get(key)
        if bucket is None:
            return False
        now = self._clock()
        if bucket.blocked_until > now:
            return True
        if bucket.blocked_until:
            self._buckets.pop(key, None)
        return False

    def fail(self, key: str) -> None:
        now = self._clock()
        bucket = self._buckets.setdefault(key, _Bucket())
        bucket.failures = [
            at for at in bucket.failures if now - at < self._window_s
        ]
        bucket.failures.append(now)
        if len(bucket.failures) >= self._max_failures:
            bucket.blocked_until = now + self._block_s
            bucket.failures.clear()
        self._sweep(now)

    def succeed(self, key: str) -> None:
        self._buckets.pop(key, None)

    def reset(self) -> None:
        self._buckets.clear()

    def _sweep(self, now: float) -> None:
        """Bound memory: forget peers with no live failures and no active block."""
        if len(self._buckets) <= 1024:
            return
        stale = [
            key
            for key, bucket in self._buckets.items()
            if bucket.blocked_until <= now
            and all(now - at >= self._window_s for at in bucket.failures)
        ]
        for key in stale:
            self._buckets.pop(key, None)


auth_failures = AuthFailureLimiter()
