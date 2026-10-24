"""Product copy loaded from ``docs/product/copy.yaml``.

Copy is reviewed with the answer policy, so it lives in a data file, not in Python string literals.
"""

from __future__ import annotations

from collections.abc import Sequence
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
    stage_scheduled: str = ""
    stage_waiting: str = ""
    invalid_answer: dict[str, str] | None = None
    not_understood: str = ""
    searching: str = ""
    file_received: str = ""
    source_one: str = ""
    source_many: str = ""
    survey_progress: str = ""
    survey_ack: str = ""
    survey_ack_open: str = ""
    stage_progress: str = ""
    post_run_benefits: str = ""
    post_run_menu: tuple[tuple[str, str], ...] = ()

    def source_line(self, names: Sequence[str]) -> str:
        """A human-readable source line instead of the raw ``[doc#chunk]`` markers.

        Live 2026-10-24: the employee saw ``[company/workspace-rules#0]`` in the chat, which reads
        as an internal leak. The chunk id still reaches the audit and the question log.
        """
        unique = tuple(dict.fromkeys(name for name in names if name))
        if not unique:
            return ""
        template = self.source_one if len(unique) == 1 else self.source_many
        return template.format(names=", ".join(unique))

    def survey_question(self, index: int, total: int) -> str:
        return self.survey_progress.format(index=index, total=total)

    def survey_acknowledgement(self, value: str | None) -> str:
        if not value:
            return self.survey_ack_open
        return self.survey_ack.format(value=value)

    def escalation_for(self, reason: EscalationReason) -> str:
        try:
            return self.escalation[reason.value]
        except KeyError:
            raise CopyError(f"no escalation copy for {reason.value!r}") from None

    def reminder(self, text: str) -> str:
        return f"{self.reminder_prefix}{text}"

    def answer_hint(self, kind: str) -> str:
        """A hint for a rejected survey answer so the same question is not just repeated."""
        hints = self.invalid_answer or {}
        return hints.get(kind, hints.get("open", ""))


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
        stage_scheduled=_text(raw, "stage_scheduled", path),
        stage_waiting=_text(raw, "stage_waiting", path),
        invalid_answer=_hints(raw, path),
        not_understood=_text(raw, "not_understood", path),
        searching=_text(raw, "searching", path),
        file_received=_text(raw, "file_received", path),
        source_one=_text(raw, "source_one", path),
        source_many=_text(raw, "source_many", path),
        survey_progress=_text(raw, "survey_progress", path),
        survey_ack=_text(raw, "survey_ack", path),
        survey_ack_open=_text(raw, "survey_ack_open", path),
        stage_progress=_text(raw, "stage_progress", path),
        post_run_benefits=_text(raw, "post_run_benefits", path),
        post_run_menu=(
            ("post_benefits", "Льготы и бонусы"),
            ("post_ask", "Спросить HR"),
            ("post_reboot", "Пройти заново"),
        ),
    )


def _hints(raw: dict[object, object], path: Path) -> dict[str, str]:
    block = raw.get("invalid_answer")
    if not isinstance(block, dict):
        raise CopyError(f"{path}: missing 'invalid_answer' mapping")
    hints: dict[str, str] = {}
    for kind in ("scale", "choice", "open"):
        hints[kind] = _text(block, kind, path)
    return hints


def _text(raw: dict[object, object], key: str, path: Path) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CopyError(f"{path}: {key} must be a non-empty string")
    return value
