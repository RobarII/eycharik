"""Survey answers: validation, scale parsing, and when a reason is required."""

from __future__ import annotations

import pytest

from onboarding.core.models import Button, Question, QuestionKind, SurveyError
from onboarding.core.survey import needs_reason, parse_answer, scale_deficit, validate_survey

SCALE = Question(
    id="manager_available",
    prompt="Насколько доступен руководитель?",
    kind=QuestionKind.SCALE,
    low_threshold=8,
    reason_prompt="Что мешает?",
)
CHOICE = Question(
    id="meeting",
    prompt="Как тебя встретили коллеги?",
    kind=QuestionKind.CHOICE,
    options=(Button(id="great", text="Отлично"), Button(id="bad", text="Никак")),
)
OPEN = Question(
    id="advice",
    prompt="Что улучшить?",
    kind=QuestionKind.OPEN,
)


def test_scale_accepts_plain_number() -> None:
    assert parse_answer(SCALE, text="9").score == 9


def test_scale_accepts_number_with_suffix() -> None:
    assert parse_answer(SCALE, text="7/10").score == 7


@pytest.mark.parametrize("raw", ["0", "11", "много", ""])
def test_scale_rejects_out_of_range_and_noise(raw: str) -> None:
    with pytest.raises(SurveyError):
        parse_answer(SCALE, text=raw)


def test_low_score_requires_a_reason() -> None:
    answer = parse_answer(SCALE, text="6")

    assert needs_reason(SCALE, answer)
    assert scale_deficit(SCALE, answer) == 2


def test_comfortable_score_requires_no_reason() -> None:
    answer = parse_answer(SCALE, text="8")

    assert not needs_reason(SCALE, answer)


def test_choice_accepts_a_known_option_id() -> None:
    assert parse_answer(CHOICE, option_id="bad").option_id == "bad"


def test_choice_rejects_an_unknown_option() -> None:
    with pytest.raises(SurveyError, match="unknown option"):
        parse_answer(CHOICE, option_id="maybe")


def test_open_answer_is_trimmed() -> None:
    assert parse_answer(OPEN, text="  больше ясности  ").text == "больше ясности"


def test_duplicate_question_ids_are_rejected() -> None:
    with pytest.raises(SurveyError, match="duplicate"):
        validate_survey((SCALE, SCALE))


def test_choice_without_options_is_rejected() -> None:
    with pytest.raises(SurveyError, match="options"):
        validate_survey((Question(id="x", prompt="?", kind=QuestionKind.CHOICE),))
