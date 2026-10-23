"""Product copy loaded from ``docs/product/copy.yaml``.

Copy is reviewed with the answer policy, so it lives in a data file, not in Python string literals.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from onboarding.core.models import EscalationReason

_REQUIRED_ESCALATIONS = {reason.value for reason in EscalationReason}


class CopyError(ValueError):
    """The copy file does not satisfy its contract."""


@dataclass(frozen=True, slots=True)
class Copy:
    escalation: dict[str, str]
    reminder_prefix: str
    escalation_footer: str

    def escalation_for(self, reason: EscalationReason) -> str:
        try:
            return self.escalation[reason.value]
        except KeyError:
            raise CopyError(f"no escalation copy for {reason.value!r}") from None

    def reminder(self, text: str) -> str:
        return f"{self.reminder_prefix}{text}"


def load_copy(path: Path) -> Copy:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise CopyError(f"{path}: expected a mapping")
    escalation = raw.get("escalation")
    if not isinstance(escalation, dict):
        raise CopyError(f"{path}: missing 'escalation' mapping")
    missing = _REQUIRED_ESCALATIONS - set(escalation)
    if missing:
        raise CopyError(f"{path}: missing escalation copy for {sorted(missing)}")
    for reason, text in escalation.items():
        if not isinstance(reason, str) or not isinstance(text, str) or not text.strip():
            raise CopyError(f"{path}: escalation copy for {reason!r} must be a non-empty string")
    reminder_prefix = raw.get("reminder_prefix")
    footer = raw.get("escalation_footer")
    if not isinstance(reminder_prefix, str) or not isinstance(footer, str):
        raise CopyError(f"{path}: reminder_prefix and escalation_footer must be strings")
    return Copy(
        escalation=dict(escalation),
        reminder_prefix=reminder_prefix,
        escalation_footer=footer,
    )
