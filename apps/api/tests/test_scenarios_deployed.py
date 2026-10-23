"""What the deployed content promises: the client's timeline, and its surveys."""

from __future__ import annotations

from pathlib import Path

from onboarding.app.scenarios import ScenarioCatalog
from onboarding.core.models import QuestionKind, StepKind

SCENARIOS = Path(__file__).resolve().parents[1] / "onboarding" / "scenarios"


def catalog() -> ScenarioCatalog:
    return ScenarioCatalog.load(SCENARIOS)


def test_the_default_scenario_covers_the_client_timeline() -> None:
    scenario = catalog().active("onboarding_default")

    assert scenario.version == 2
    assert len(scenario.steps) >= 15
    surveys = [step for step in scenario.steps.values() if step.kind is StepKind.SURVEY]
    assert len(surveys) == 4


def test_the_two_week_survey_asks_nine_scale_questions() -> None:
    step = catalog().active("onboarding_default").step("week_two_survey")

    scales = [question for question in step.questions if question.kind is QuestionKind.SCALE]
    assert len(scales) == 9
    assert all(question.low_threshold == 8 for question in scales)
    assert all(question.reason_prompt for question in scales)


def test_every_scale_question_can_ask_for_a_reason() -> None:
    scenario = catalog().active("onboarding_default")

    for step in scenario.steps.values():
        for question in step.questions:
            if question.kind is QuestionKind.SCALE:
                assert question.low_threshold is not None
                assert question.reason_prompt


def test_the_plant_variant_skips_the_remote_work_question() -> None:
    office = catalog().active("onboarding_default")
    plant = catalog().active("onboarding_plant")

    office_questions = {q.id for step in office.steps.values() for q in step.questions}
    plant_questions = {q.id for step in plant.steps.values() for q in step.questions}
    assert "remote_work" in office_questions
    assert "remote_work" not in plant_questions
