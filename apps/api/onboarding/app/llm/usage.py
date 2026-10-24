"""What a provider says it charged, read in one place.

Two wire shapes report money: a chat completion and a System One response. Both put the provider's
own number in ``usage.cost``, and both are sometimes silent about it. The parser returns ``None``,
never ``0.0``: "not reported" and "free" are different facts, and an eval that conflates them
records a price nobody measured.
"""

from __future__ import annotations

import math

__all__ = ["reported_cost_usd"]


def reported_cost_usd(usage: object) -> float | None:
    """``usage.cost`` in USD, when the provider sends one; ``None`` when it does not.

    OpenRouter reports the charge here. TypeSafe's direct endpoint reports tokens and nothing else,
    which is why a ruble price stays in the profile and this number stays absent instead of guessed.
    """
    if not isinstance(usage, dict):
        return None
    cost = usage.get("cost")
    if isinstance(cost, bool) or not isinstance(cost, int | float):
        return None
    value = float(cost)
    if not math.isfinite(value) or value < 0:
        return None
    return value
