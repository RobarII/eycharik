"""Risk rules: what raises a flag, what only feeds the digest, and why."""

from __future__ import annotations

from onboarding.core.models import (
    Question,
    QuestionKind,
    RiskLevel,
    RiskSignal,
    Sentiment,
    SignalTag,
    SurveyAnswer,
)
from onboarding.core.risk import assess, assess_text, survey_signals


def test_negative_access_answer_escalates_to_recruiter() -> None:
    assessment = assess_text(
        "Доступ к порталу так и не выдали, пароль не подходит", source="survey:access"
    )

    assert assessment.level is RiskLevel.HIGH
    assert SignalTag.ACCESS in assessment.tags
    assert assessment.escalate_to == "recruiter"


def test_crisis_wording_escalates_even_without_a_tag() -> None:
    assessment = assess_text("Скоро увольняюсь, если ничего не изменится", source="survey:open")

    assert assessment.level is RiskLevel.HIGH
    assert assessment.escalate_to == "recruiter"
    assert any("crisis" in reason for reason in assessment.reasons)


def test_positive_answer_stays_low() -> None:
    assessment = assess_text("Все отлично, коллеги помогли разобраться", source="survey:open")

    assert assessment.level is RiskLevel.LOW
    assert assessment.escalate_to is None


def test_low_score_alone_feeds_the_digest() -> None:
    signal = RiskSignal(
        source="survey:manager",
        sentiment=Sentiment.NEUTRAL,
        tags=(SignalTag.MANAGER,),
        confidence=0.9,
        score=3,
        low_threshold=8,
    )

    assessment = assess([signal])

    assert assessment.level is RiskLevel.MEDIUM
    assert assessment.escalate_to is None
    assert assessment.tags == (SignalTag.MANAGER,)


def test_slightly_low_score_is_medium() -> None:
    signal = RiskSignal(
        source="survey:workload",
        sentiment=Sentiment.NEUTRAL,
        tags=(SignalTag.WORKLOAD,),
        confidence=0.9,
        score=7,
        low_threshold=8,
    )

    assert assess([signal]).level is RiskLevel.MEDIUM


def test_low_confidence_negative_answer_is_not_auto_escalated() -> None:
    signal = RiskSignal(
        source="survey:open",
        sentiment=Sentiment.NEGATIVE,
        tags=(SignalTag.COLLEAGUES,),
        confidence=0.3,
        text="что-то не так с командой",
    )

    assessment = assess([signal])

    assert assessment.level is RiskLevel.MEDIUM
    assert assessment.escalate_to is None
    assert any("low classifier confidence" in reason for reason in assessment.reasons)


def test_score_is_added_when_text_and_scale_both_complain() -> None:
    signals = [
        RiskSignal(
            source="survey:manager_text",
            sentiment=Sentiment.NEGATIVE,
            tags=(SignalTag.MANAGER,),
            confidence=0.8,
            text="руководитель не отвечает",
        ),
        RiskSignal(
            source="survey:manager_score",
            sentiment=Sentiment.NEUTRAL,
            tags=(SignalTag.MANAGER,),
            confidence=0.9,
            score=7,
            low_threshold=8,
        ),
    ]

    assessment = assess(signals)

    assert assessment.level is RiskLevel.HIGH
    assert assessment.score == 4
    assert assessment.tags == (SignalTag.MANAGER,)


def test_tags_are_unique_and_keep_first_seen_order() -> None:
    signals = [
        RiskSignal(
            source="a",
            sentiment=Sentiment.NEUTRAL,
            tags=(SignalTag.IT, SignalTag.ACCESS),
            confidence=0.9,
        ),
        RiskSignal(
            source="b",
            sentiment=Sentiment.NEUTRAL,
            tags=(SignalTag.ACCESS, SignalTag.HR),
            confidence=0.9,
        ),
    ]

    assert assess(signals).tags == (SignalTag.IT, SignalTag.ACCESS, SignalTag.HR)


def test_empty_input_is_low() -> None:
    assessment = assess([])

    assert assessment.level is RiskLevel.LOW
    assert assessment.score == 0
    assert assessment.reasons == ()


def test_scale_answer_becomes_a_signal_without_words() -> None:
    question = Question(
        id="manager",
        prompt="Насколько доступен руководитель?",
        kind=QuestionKind.SCALE,
        low_threshold=8,
    )

    signals = survey_signals((question,), (SurveyAnswer(question_id="manager", score=6),))

    assert len(signals) == 1
    assert signals[0].score == 6
    assert signals[0].tags == ()


def test_survey_signals_combine_text_and_score() -> None:
    question = Question(
        id="manager",
        prompt="Насколько доступен руководитель?",
        kind=QuestionKind.SCALE,
        low_threshold=8,
    )
    answers = (
        SurveyAnswer(question_id="manager", score=7),
        SurveyAnswer(question_id="manager", text="Руководитель не отвечает, конфликт в команде"),
    )

    assessment = assess(survey_signals((question,), answers))

    assert assessment.level is RiskLevel.HIGH
    assert assessment.escalate_to == "recruiter"
    assert SignalTag.MANAGER in assessment.tags
