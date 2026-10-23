from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from onboarding.core.models import ScenarioError, StepKind
from onboarding.core.scenario import parse_scenario

from .conftest import scenario_document


def test_parses_a_valid_document(scenario: Any) -> None:
    assert scenario.id == "onboarding_default"
    assert scenario.version == 1
    assert scenario.start == "welcome"
    assert scenario.step("welcome").kind is StepKind.SEND
    assert scenario.step("done").kind is StepKind.TERMINAL


def test_steps_mapping_is_read_only(scenario: Any) -> None:
    with pytest.raises(TypeError):
        scenario.steps["x"] = scenario.step("done")  # type: ignore[index]


def test_rejects_unknown_top_level_key() -> None:
    document = scenario_document()
    document["owner"] = "hr"
    with pytest.raises(ScenarioError, match="unknown keys"):
        parse_scenario(document)


def test_rejects_unknown_step_key() -> None:
    document = scenario_document()
    document["steps"][0]["delay"] = 1
    with pytest.raises(ScenarioError, match="unknown keys"):
        parse_scenario(document)


def test_rejects_duplicate_step_id() -> None:
    document = scenario_document()
    document["steps"][1]["id"] = "welcome"
    with pytest.raises(ScenarioError, match="duplicate step id"):
        parse_scenario(document)


def test_rejects_missing_required_key_for_kind() -> None:
    document = scenario_document()
    del document["steps"][0]["next"]
    with pytest.raises(ScenarioError, match="requires"):
        parse_scenario(document)


def test_rejects_key_forbidden_by_kind() -> None:
    document = scenario_document()
    document["steps"][3]["keyboard"] = []
    with pytest.raises(ScenarioError, match="forbids"):
        parse_scenario(document)


def test_rejects_unknown_start() -> None:
    document = scenario_document()
    document["start"] = "nowhere"
    with pytest.raises(ScenarioError, match="unknown step 'nowhere'"):
        parse_scenario(document)


def test_rejects_dangling_reference() -> None:
    document = scenario_document()
    document["steps"][2]["routes"] = {"default": "ghost"}
    with pytest.raises(ScenarioError, match="unknown step 'ghost'"):
        parse_scenario(document)


def test_rejects_unreachable_step() -> None:
    document = scenario_document()
    document["steps"].append({"id": "orphan", "kind": "terminal", "outcome": "completed"})
    with pytest.raises(ScenarioError, match="unreachable"):
        parse_scenario(document)


def test_rejects_button_without_route() -> None:
    document = scenario_document()
    document["steps"][1]["keyboard"][0].append({"id": "later", "text": "Позже"})
    with pytest.raises(ScenarioError, match="without a route"):
        parse_scenario(document)


def test_rejects_route_to_unknown_button() -> None:
    document = scenario_document()
    document["steps"][1]["routes"]["ghost"] = "done"
    with pytest.raises(ScenarioError, match="unknown buttons"):
        parse_scenario(document)


def test_rejects_duplicate_button_id() -> None:
    document = scenario_document()
    document["steps"][2]["keyboard"] = [[{"id": "done", "text": "Ещё"}]]  # type: ignore[index]
    document["steps"][2]["expects"] = "button"  # type: ignore[index]
    document["steps"][2]["routes"] = {"done": "done"}  # type: ignore[index]
    with pytest.raises(ScenarioError, match="duplicate button id"):
        parse_scenario(document)


def test_rejects_keyboard_wider_than_three() -> None:
    document = scenario_document()
    document["steps"][1]["keyboard"] = [
        [{"id": f"b{index}", "text": "x"} for index in range(4)]
    ]
    document["steps"][1]["routes"] = {f"b{index}": "done" for index in range(4)}
    with pytest.raises(ScenarioError, match="at most 3 buttons"):
        parse_scenario(document)


def test_rejects_timeout_with_bad_action() -> None:
    document = scenario_document()
    document["steps"][1]["timeout"]["action"] = "delete"
    with pytest.raises(ScenarioError, match="action"):
        parse_scenario(document)


def test_rejects_unknown_kind() -> None:
    document = scenario_document()
    document["steps"][0]["kind"] = "email"
    with pytest.raises(ScenarioError, match="kind"):
        parse_scenario(document)


def test_rejects_too_long_message() -> None:
    document = scenario_document()
    document["steps"][0]["message"] = "а" * 4001
    with pytest.raises(ScenarioError, match="4000"):
        parse_scenario(document)


def test_rejects_duplicate_route_keys_before_parsing() -> None:
    document: dict[str, Any] = deepcopy(scenario_document())
    assert document["steps"][1]["routes"] == {"done": "documents"}
