"""Pure retention rules.

Retention is a decision, not a query: how old is too old, and what survives in the audit log when
the personal part is gone. The database adapter applies these rules; it does not invent them. This
module is in ``core/`` and therefore has no clock, no I/O and no imports outside the standard
library.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta

# Keys that may carry an employee's own words. They are stripped when a row outlives the
# retention window; the event name, ids, levels and timestamps stay so a count remains traceable.
PERSONAL_AUDIT_KEYS = frozenset({"evidence", "quote", "question", "text"})


def cutoff(now: datetime, days: int) -> datetime:
    """The oldest timestamp that is still inside the retention window."""
    if days < 1:
        raise ValueError("retention days must be at least 1")
    return now - timedelta(days=days)


def expired(at: datetime, now: datetime, days: int) -> bool:
    """True when a row written at ``at`` is outside the window and must be purged."""
    return at < cutoff(now, days)


def redact_fields(fields: Mapping[str, object]) -> dict[str, object]:
    """Drop personal fragments from an audit payload and mark it redacted.

    The function is idempotent: a payload without personal keys comes back unchanged, so a second
    purge pass does not grow the row.
    """
    cleaned = {key: value for key, value in fields.items() if key not in PERSONAL_AUDIT_KEYS}
    if len(cleaned) != len(fields):
        cleaned["redacted"] = True
    return cleaned
