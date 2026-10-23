"""Validate a scenario document and turn it into frozen domain values.

The parser is strict on purpose: an unknown key, a dangling next step, or an unreachable step is
a deployment error, not a runtime surprise on an employee's first day. Messages name the path that
failed, so a rejected document is fixable without a debugger.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from types import MappingProxyType
from typing import Any

from .models import (
    MAX_MESSAGE_CHARS,
    MAX_TITLE_CHARS,
    Button,
    Expects,
    Keyboard,
    Outcome,
    Scenario,
    ScenarioError,
    Step,
    StepKind,
    Timeout,
    TimeoutAction,
)

_TOP_KEYS = {"id", "version", "title", "start", "steps"}
_STEP_KEYS = {
    "id",
    "kind",
    "title",
    "message",
    "keyboard",
    "expects",
    "routes",
    "next",
    "timeout",
    "escalate_to",
    "outcome",
}
_REQUIRED_BY_KIND = {
    StepKind.SEND: {"message", "next"},
    StepKind.WAIT: {"expects"},
    StepKind.TERMINAL: {"outcome"},
}
_FORBIDDEN_BY_KIND = {
    StepKind.SEND: {"expects", "routes", "timeout", "outcome"},
    StepKind.WAIT: {"next", "outcome"},
    StepKind.TERMINAL: {"message", "keyboard", "expects", "routes", "next", "timeout"},
}
_MAX_KEYBOARD_ROWS = 3
_MAX_BUTTONS_PER_ROW = 3


def parse_scenario(raw: Mapping[str, Any]) -> Scenario:
    """Build a validated scenario or raise :class:`ScenarioError` naming the broken path."""
    _reject_unknown(raw, _TOP_KEYS, "scenario")
    scenario_id = _text(raw, "id", "scenario")
    version = _integer(raw, "version", "scenario")
    title = _text(raw, "title", "scenario")
    start = _text(raw, "start", "scenario")
    raw_steps = _list(raw, "steps", "scenario")
    if version < 1:
        raise ScenarioError("scenario.version must be at least 1")

    steps: dict[str, Step] = {}
    button_ids: set[str] = set()
    for position, raw_step in enumerate(raw_steps):
        path = f"scenario.steps[{position}]"
        step = _parse_step(_mapping(raw_step, path), path, button_ids)
        if step.id in steps:
            raise ScenarioError(f"{path}: duplicate step id {step.id!r}")
        steps[step.id] = step

    if not steps:
        raise ScenarioError("scenario.steps must not be empty")
    if start not in steps:
        raise ScenarioError(f"scenario.start references unknown step {start!r}")
    _check_references(steps)
    _check_reachability(steps, start)
    return Scenario(
        id=scenario_id,
        version=version,
        title=title,
        start=start,
        steps=MappingProxyType(steps),
    )


def _parse_step(raw: Mapping[str, Any], path: str, button_ids: set[str]) -> Step:
    _reject_unknown(raw, _STEP_KEYS, path)
    step_id = _text(raw, "id", path)
    kind = _kind(raw, path)
    missing = _REQUIRED_BY_KIND[kind] - raw.keys()
    if missing:
        raise ScenarioError(f"{path}: step kind {kind.value!r} requires {sorted(missing)}")
    forbidden = _FORBIDDEN_BY_KIND[kind] & raw.keys()
    if forbidden:
        raise ScenarioError(f"{path}: step kind {kind.value!r} forbids {sorted(forbidden)}")

    message = _text(raw, "message", path) if "message" in raw else None
    if message is not None and len(message) > MAX_MESSAGE_CHARS:
        raise ScenarioError(f"{path}: message exceeds {MAX_MESSAGE_CHARS} characters")

    title = _text(raw, "title", path) if "title" in raw else None
    if title is not None and len(title) > MAX_TITLE_CHARS:
        raise ScenarioError(f"{path}: title exceeds {MAX_TITLE_CHARS} characters")

    keyboard = _parse_keyboard(raw, path, button_ids)
    routes = _routes(raw, path)
    timeout = _timeout(raw, path)
    expects = Expects(raw["expects"]) if "expects" in raw else None
    outcome = Outcome(raw["outcome"]) if "outcome" in raw else None
    escalate_to = _text(raw, "escalate_to", path) if "escalate_to" in raw else None
    if escalate_to is not None and escalate_to not in {"recruiter", "hr"}:
        raise ScenarioError(f"{path}: escalate_to must be 'recruiter' or 'hr'")

    if expects is Expects.BUTTON:
        unknown_buttons = set(routes) - button_ids - {"default"}
        if unknown_buttons:
            raise ScenarioError(
                f"{path}: routes reference unknown buttons {sorted(unknown_buttons)}"
            )
        unrouted = button_ids - set(routes)
        if unrouted:
            raise ScenarioError(f"{path}: buttons without a route {sorted(unrouted)}")

    return Step(
        id=step_id,
        kind=kind,
        title=title,
        message=message,
        keyboard=keyboard,
        expects=expects,
        routes=routes,
        next_step=_text(raw, "next", path) if "next" in raw else None,
        timeout=timeout,
        escalate_to=escalate_to,
        outcome=outcome,
    )


def _parse_keyboard(raw: Mapping[str, Any], path: str, button_ids: set[str]) -> Keyboard:
    if "keyboard" not in raw:
        return ()
    rows = _list(raw, "keyboard", path)
    if len(rows) > _MAX_KEYBOARD_ROWS:
        raise ScenarioError(f"{path}.keyboard: at most {_MAX_KEYBOARD_ROWS} rows")
    parsed: list[tuple[Button, ...]] = []
    for row_index, raw_row in enumerate(rows):
        row_path = f"{path}.keyboard[{row_index}]"
        raw_buttons = _list_value(raw_row, row_path)
        if not raw_buttons:
            raise ScenarioError(f"{row_path}: a row must contain at least one button")
        if len(raw_buttons) > _MAX_BUTTONS_PER_ROW:
            raise ScenarioError(f"{row_path}: at most {_MAX_BUTTONS_PER_ROW} buttons")
        buttons: list[Button] = []
        for button_index, raw_button in enumerate(raw_buttons):
            button_path = f"{row_path}[{button_index}]"
            item = _mapping(raw_button, button_path)
            _reject_unknown(item, {"id", "text"}, button_path)
            button = Button(
                id=_text(item, "id", button_path),
                text=_text(item, "text", button_path),
            )
            if button.id in button_ids:
                raise ScenarioError(f"{button_path}: duplicate button id {button.id!r}")
            button_ids.add(button.id)
            buttons.append(button)
        parsed.append(tuple(buttons))
    return tuple(parsed)


def _timeout(raw: Mapping[str, Any], path: str) -> Timeout | None:
    if "timeout" not in raw:
        return None
    timeout_path = f"{path}.timeout"
    item = _mapping(raw["timeout"], timeout_path)
    _reject_unknown(item, {"after_hours", "action", "next"}, timeout_path)
    hours = item.get("after_hours")
    if isinstance(hours, bool) or not isinstance(hours, int | float) or hours <= 0:
        raise ScenarioError(f"{timeout_path}.after_hours must be a positive number")
    try:
        action = TimeoutAction(str(item.get("action")))
    except ValueError:
        raise ScenarioError(
            f"{timeout_path}.action must be one of {[a.value for a in TimeoutAction]}"
        ) from None
    next_step = _text(item, "next", timeout_path) if "next" in item else None
    return Timeout(after=timedelta(hours=hours), action=action, next_step=next_step)


def _routes(raw: Mapping[str, Any], path: str) -> Mapping[str, str]:
    if "routes" not in raw:
        return MappingProxyType({})
    item = _mapping(raw["routes"], f"{path}.routes")
    routes: dict[str, str] = {}
    for key, value in item.items():
        if not isinstance(key, str) or not key:
            raise ScenarioError(f"{path}.routes: keys must be non-empty strings")
        if not isinstance(value, str) or not value:
            raise ScenarioError(f"{path}.routes[{key!r}]: target must be a non-empty string")
        routes[key] = value
    return MappingProxyType(routes)


def _check_references(steps: Mapping[str, Step]) -> None:
    for step in steps.values():
        targets = [step.next_step, *(step.routes.values() if step.routes else ())]
        if step.timeout is not None:
            targets.append(step.timeout.next_step)
        for target in targets:
            if target is not None and target not in steps:
                raise ScenarioError(f"step {step.id!r} references unknown step {target!r}")


def _check_reachability(steps: Mapping[str, Step], start: str) -> None:
    seen: set[str] = set()
    queue = [start]
    while queue:
        current = queue.pop()
        if current in seen:
            continue
        seen.add(current)
        step = steps[current]
        targets = [step.next_step, *(step.routes.values() if step.routes else ())]
        if step.timeout is not None:
            targets.append(step.timeout.next_step)
        queue.extend(target for target in targets if target is not None)
    unreachable = sorted(set(steps) - seen)
    if unreachable:
        raise ScenarioError(f"unreachable steps {unreachable}")


def _kind(raw: Mapping[str, Any], path: str) -> StepKind:
    value = raw.get("kind")
    try:
        return StepKind(str(value))
    except ValueError:
        raise ScenarioError(f"{path}.kind must be one of {[k.value for k in StepKind]}") from None


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ScenarioError(f"{path} must be a mapping")
    return value


def _text(raw: Mapping[str, Any], key: str, path: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ScenarioError(f"{path}.{key} must be a non-empty string")
    return value


def _integer(raw: Mapping[str, Any], key: str, path: str) -> int:
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ScenarioError(f"{path}.{key} must be an integer")
    return value


def _list(raw: Mapping[str, Any], key: str, path: str) -> list[Any]:
    return _list_value(raw.get(key), f"{path}.{key}")


def _list_value(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ScenarioError(f"{path} must be a list")
    return value


def _reject_unknown(raw: Mapping[str, Any], allowed: set[str], path: str) -> None:
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ScenarioError(f"{path}: unknown keys {unknown}")
