from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from typing import Any

import pytest

from onboarding.core.models import QuestionKind, ScenarioError, StepKind, Tone
from onboarding.core.scenario import parse_scenario

from .conftest import scenario_document


def test_parses_a_valid_document(scenario: Any) -> None:
    assert scenario.id == "onboarding_default"
    assert scenario.version == 1
    assert scenario.start == "welcome"
    assert scenario.step("welcome").kind is StepKind.SEND
    assert scenario.step("done").kind is StepKind.TERMINAL


def test_parses_a_bundled_image_on_a_send_and_a_terminal_step() -> None:
    document = scenario_document()
    document["steps"][0]["image"] = "welcome.jpg"
    document["steps"][3]["image"] = "goodbye.jpg"

    scenario = parse_scenario(document)

    assert scenario.step("welcome").image == "welcome.jpg"
    assert scenario.step("done").image == "goodbye.jpg"


@pytest.mark.parametrize("name", ["../secret.jpg", "welcome.gif", "Welcome.jpg", "a/b.jpg"])
def test_rejects_an_image_outside_the_bundle(name: str) -> None:
    document = scenario_document()
    document["steps"][0]["image"] = name

    with pytest.raises(ScenarioError, match="bundled jpg/png name"):
        parse_scenario(document)


def test_steps_mapping_is_read_only(scenario: Any) -> None:
    with pytest.raises(TypeError):
        scenario.steps["x"] = scenario.step("done")  # type: ignore[index]


def test_parses_tone_routes_and_an_informal_message() -> None:
    document = scenario_document()
    step = document["steps"][1]
    step["tone"] = {"done": "informal"}
    step["informal_message"] = "Отметься, пожалуйста."

    scenario = parse_scenario(document)

    assert scenario.step("checklist").tone_routes == {"done": Tone.INFORMAL}
    assert scenario.step("checklist").informal_message == "Отметься, пожалуйста."


def test_rejects_a_tone_route_to_an_unknown_button() -> None:
    document = scenario_document()
    document["steps"][1]["tone"] = {"missing": "informal"}

    with pytest.raises(ScenarioError, match="tone references unknown buttons"):
        parse_scenario(document)


def test_rejects_a_tone_on_a_step_without_buttons() -> None:
    document = scenario_document()
    document["steps"][0]["tone"] = {"done": "informal"}

    with pytest.raises(ScenarioError, match="tone requires a step that expects a button"):
        parse_scenario(document)


def test_rejects_a_title_longer_than_the_schema_allows() -> None:
    document = scenario_document()
    document["steps"][0]["title"] = "я" * 81

    with pytest.raises(ScenarioError, match="title exceeds"):
        parse_scenario(document)


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
    document["steps"][1]["keyboard"] = [[{"id": f"b{index}", "text": "x"} for index in range(4)]]
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


def test_keyboard_routes_are_checked_per_step() -> None:
    document = {
        "id": "two_keyboards",
        "version": 1,
        "title": "Две клавиатуры",
        "start": "first",
        "steps": [
            {
                "id": "first",
                "kind": "wait",
                "message": "Первый",
                "expects": "button",
                "keyboard": [[{"id": "a", "text": "A"}]],
                "routes": {"a": "second"},
                "timeout": {"after_hours": 1, "action": "remind"},
            },
            {
                "id": "second",
                "kind": "wait",
                "message": "Второй",
                "expects": "button",
                "keyboard": [[{"id": "b", "text": "B"}]],
                "routes": {"b": "done"},
                "timeout": {"after_hours": 1, "action": "remind"},
            },
            {"id": "done", "kind": "terminal", "outcome": "completed"},
        ],
    }

    scenario = parse_scenario(document)

    assert scenario.step("second").keyboard[0][0].id == "b"


def test_parses_segments_and_delay_hours() -> None:
    doc = scenario_document()
    doc["segments"] = ["segment_a", "segment_b"]
    doc["steps"][0]["delay_hours"] = 2.5
    scenario = parse_scenario(doc)
    assert scenario.segments == ("segment_a", "segment_b")
    assert scenario.step("welcome").delay == timedelta(hours=2.5)


def test_parses_survey_with_choice_scale_and_open() -> None:
    doc = {
        "id": "survey_valid",
        "version": 1,
        "title": "Опрос",
        "start": "s",
        "steps": [
            {
                "id": "s",
                "kind": "survey",
                "questions": [
                    {
                        "id": "q1",
                        "kind": "choice",
                        "prompt": "Choose",
                        "options": [{"id": "o1", "text": "Opt 1"}],
                    },
                    {
                        "id": "q2",
                        "kind": "scale",
                        "prompt": "Rate",
                        "low_threshold": 3,
                        "reason_prompt": "Why low?",
                    },
                    {
                        "id": "q3",
                        "kind": "open",
                        "prompt": "Feedback",
                    },
                ],
                "next": "done",
            },
            {"id": "done", "kind": "terminal", "outcome": "completed"},
        ],
    }
    scenario = parse_scenario(doc)
    step = scenario.step("s")
    assert len(step.questions) == 3
    assert step.questions[0].options[0].id == "o1"
    assert step.questions[1].low_threshold == 3
    assert step.questions[2].kind is QuestionKind.OPEN


def test_reachability_handles_cycles_and_diamonds() -> None:
    doc = {
        "id": "diamond",
        "version": 1,
        "title": "Diamond",
        "start": "first",
        "steps": [
            {
                "id": "first",
                "kind": "wait",
                "message": "Start",
                "expects": "button",
                "keyboard": [[{"id": "left", "text": "L"}, {"id": "right", "text": "R"}]],
                "routes": {"left": "mid_a", "right": "mid_b"},
            },
            {"id": "mid_a", "kind": "send", "message": "A", "next": "done"},
            {"id": "mid_b", "kind": "send", "message": "B", "next": "done"},
            {"id": "done", "kind": "terminal", "outcome": "completed"},
        ],
    }
    scenario = parse_scenario(doc)
    assert scenario.step("done").id == "done"


def test_rejects_version_less_than_one() -> None:
    doc = scenario_document()
    doc["version"] = 0
    with pytest.raises(ScenarioError, match="version must be at least 1"):
        parse_scenario(doc)


def test_rejects_empty_steps() -> None:
    doc = scenario_document()
    doc["steps"] = []
    with pytest.raises(ScenarioError, match="steps must not be empty"):
        parse_scenario(doc)


def test_rejects_invalid_escalate_to() -> None:
    doc = scenario_document()
    doc["steps"][1]["escalate_to"] = "ceo"
    with pytest.raises(ScenarioError, match="escalate_to must be 'recruiter' or 'hr'"):
        parse_scenario(doc)


def test_rejects_keyboard_with_too_many_rows() -> None:
    doc = scenario_document()
    doc["steps"][1]["keyboard"] = [[{"id": f"b{i}", "text": "x"}] for i in range(6)]
    doc["steps"][1]["routes"] = {f"b{i}": "done" for i in range(6)}
    with pytest.raises(ScenarioError, match="at most 3 rows"):
        parse_scenario(doc)


def test_rejects_empty_keyboard_row() -> None:
    doc = scenario_document()
    doc["steps"][1]["keyboard"] = [[]]
    with pytest.raises(ScenarioError, match="row must contain at least one button"):
        parse_scenario(doc)


def test_rejects_invalid_tone_value() -> None:
    doc = scenario_document()
    doc["steps"][1]["tone"] = {"done": "super_casual"}
    with pytest.raises(ScenarioError, match=r"tone\['done'\] must be one of"):
        parse_scenario(doc)


def test_rejects_non_positive_delay_hours() -> None:
    doc = scenario_document()
    doc["steps"][0]["delay_hours"] = -1
    with pytest.raises(ScenarioError, match="delay_hours must be a positive number"):
        parse_scenario(doc)


def test_rejects_non_positive_timeout_after_hours() -> None:
    doc = scenario_document()
    doc["steps"][1]["timeout"]["after_hours"] = 0
    with pytest.raises(ScenarioError, match="after_hours must be a positive number"):
        parse_scenario(doc)


def test_rejects_empty_routes_key_or_value() -> None:
    doc1 = scenario_document()
    doc1["steps"][2]["routes"] = {"": "done"}
    with pytest.raises(ScenarioError, match="keys must be non-empty strings"):
        parse_scenario(doc1)

    doc2 = scenario_document()
    doc2["steps"][2]["routes"] = {"default": ""}
    with pytest.raises(
        ScenarioError, match=r"routes\['default'\]: target must be a non-empty string"
    ):
        parse_scenario(doc2)


def test_rejects_invalid_segments() -> None:
    doc1 = scenario_document()
    doc1["segments"] = ["  "]
    with pytest.raises(ScenarioError, match="must be a non-empty string"):
        parse_scenario(doc1)

    doc2 = scenario_document()
    doc2["segments"] = ["it", "it"]
    with pytest.raises(ScenarioError, match="duplicate segment 'it'"):
        parse_scenario(doc2)


def test_rejects_bad_question_kind_and_options_in_open() -> None:
    doc1 = {
        "id": "survey_bad_kind",
        "version": 1,
        "title": "Bad survey",
        "start": "s",
        "steps": [
            {
                "id": "s",
                "kind": "survey",
                "questions": [{"id": "q", "kind": "unknown", "prompt": "Hi"}],
                "next": "done",
            },
            {"id": "done", "kind": "terminal", "outcome": "completed"},
        ],
    }
    with pytest.raises(ScenarioError, match=r"kind must be one of"):
        parse_scenario(doc1)

    doc2 = {
        "id": "survey_open_options",
        "version": 1,
        "title": "Bad survey",
        "start": "s",
        "steps": [
            {
                "id": "s",
                "kind": "survey",
                "questions": [
                    {
                        "id": "q",
                        "kind": "open",
                        "prompt": "Hi",
                        "options": [{"id": "o", "text": "O"}],
                    }
                ],
                "next": "done",
            },
            {"id": "done", "kind": "terminal", "outcome": "completed"},
        ],
    }
    with pytest.raises(ScenarioError, match="only a choice question takes options"):
        parse_scenario(doc2)


def test_rejects_scale_threshold_not_integer() -> None:
    doc = {
        "id": "survey_scale",
        "version": 1,
        "title": "Bad survey",
        "start": "s",
        "steps": [
            {
                "id": "s",
                "kind": "survey",
                "questions": [
                    {
                        "id": "q",
                        "kind": "scale",
                        "prompt": "Rate",
                        "low_threshold": "not_an_int",
                        "reason_prompt": "Why?",
                    }
                ],
                "next": "done",
            },
            {"id": "done", "kind": "terminal", "outcome": "completed"},
        ],
    }
    with pytest.raises(ScenarioError, match="low_threshold must be an integer"):
        parse_scenario(doc)


def test_rejects_duplicate_option_id() -> None:
    doc = {
        "id": "survey_choice",
        "version": 1,
        "title": "Bad survey",
        "start": "s",
        "steps": [
            {
                "id": "s",
                "kind": "survey",
                "questions": [
                    {
                        "id": "q",
                        "kind": "choice",
                        "prompt": "Choose",
                        "options": [
                            {"id": "opt1", "text": "A"},
                            {"id": "opt1", "text": "B"},
                        ],
                    }
                ],
                "next": "done",
            },
            {"id": "done", "kind": "terminal", "outcome": "completed"},
        ],
    }
    with pytest.raises(ScenarioError, match="duplicate option id 'opt1'"):
        parse_scenario(doc)


def test_rejects_non_mapping_or_non_list_structures() -> None:
    doc = scenario_document()
    doc["steps"] = ["not a mapping"]
    with pytest.raises(ScenarioError, match="must be a mapping"):
        parse_scenario(doc)

    doc_bad_list = scenario_document()
    doc_bad_list["steps"] = "not a list"
    with pytest.raises(ScenarioError, match="must be a list"):
        parse_scenario(doc_bad_list)

    doc_bad_str = scenario_document()
    doc_bad_str["title"] = 123
    with pytest.raises(ScenarioError, match="title must be a non-empty string"):
        parse_scenario(doc_bad_str)

    doc_bad_int = scenario_document()
    doc_bad_int["version"] = "1"
    with pytest.raises(ScenarioError, match="version must be an integer"):
        parse_scenario(doc_bad_int)




