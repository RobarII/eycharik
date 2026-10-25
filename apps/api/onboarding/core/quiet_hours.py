"""Quiet hours: nobody wants a stage reminder at three in the morning.

The rule is pure: it takes the moment it is called at and returns the moment a proactive message
may go out. Answers to a person who is awake are never delayed through here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

WEEK_END = 24


@dataclass(frozen=True, slots=True)
class QuietHours:
    """A window in local time when the bot keeps proactive messages to itself."""

    start_hour: int
    end_hour: int
    timezone: str = "Europe/Moscow"

    def __post_init__(self) -> None:
        for hour in (self.start_hour, self.end_hour):
            if not 0 <= hour <= WEEK_END:
                raise ValueError(f"quiet hour {hour} is out of range")
        if self.start_hour == self.end_hour:
            raise ValueError("quiet hours must have a non-empty window")
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError:
            raise ValueError(f"unknown timezone {self.timezone!r}") from None

    def next_allowed(self, now: datetime) -> datetime:
        """Return ``now`` when it is day, else the first allowed minute in the same timezone."""
        zone = ZoneInfo(self.timezone)
        moment = now.replace(tzinfo=UTC) if now.tzinfo is None else now
        local = moment.astimezone(zone)
        if not self.is_quiet(local):
            return moment
        target = local.replace(hour=self.end_hour % WEEK_END, minute=0, second=0, microsecond=0)
        if self.wraps_midnight() or self.end_hour > local.hour:
            target = target if target > local else target + timedelta(days=1)
        else:
            target += timedelta(days=1)
        return target.astimezone(UTC)

    def wraps_midnight(self) -> bool:
        return self.start_hour > self.end_hour

    def is_quiet(self, local: datetime) -> bool:
        hour = local.hour
        if self.wraps_midnight():
            return hour >= self.start_hour or hour < self.end_hour
        return self.start_hour <= hour < self.end_hour
