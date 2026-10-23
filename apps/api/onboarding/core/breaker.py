"""A circuit breaker as a value object.

Kept pure so the policy is tested with a fake clock instead of a sleep. The gateway replaces its
breaker with the value returned by :meth:`record`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class CircuitBreaker:
    threshold: int = 3
    cooldown: timedelta = timedelta(seconds=30)
    failures: int = 0
    opened_at: datetime | None = None

    def allows(self, now: datetime) -> bool:
        if self.opened_at is None:
            return True
        return now >= self.opened_at + self.cooldown

    def record_success(self) -> CircuitBreaker:
        return replace(self, failures=0, opened_at=None)

    def record_failure(self, now: datetime) -> CircuitBreaker:
        failures = self.failures + 1
        if failures >= self.threshold and self.opened_at is None:
            return replace(self, failures=failures, opened_at=now)
        return replace(self, failures=failures)

    @property
    def is_open(self) -> bool:
        return self.opened_at is not None
