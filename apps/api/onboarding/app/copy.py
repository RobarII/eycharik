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
    completion: str
    help: str = ""
    unknown_command: str = ""
    ask_question: str = ""
    no_next_stage: str = ""

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
    reminder_prefix = _text(raw, "reminder_prefix", path)
    footer = _text(raw, "escalation_footer", path)
    completion = _text(raw, "completion", path)
    return Copy(
        escalation=dict(escalation),
        reminder_prefix=reminder_prefix,
        escalation_footer=footer,
        completion=completion,
        help=_text(raw, "help", path),
        unknown_command=_text(raw, "unknown_command", path),
        ask_question=_text(raw, "ask_question", path),
        no_next_stage=_text(raw, "no_next_stage", path),
    )


def _text(raw: dict[object, object], key: str, path: Path) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CopyError(f"{path}: {key} must be a non-empty string")
    return value
