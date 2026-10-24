"""Survey answers as pure values: validate one answer, decide whether a reason is required.

The worker owns transport and storage. This module owns the rules that decide whether an answer is
acceptable at all and whether a low score opens the follow-up question. Nothing here knows about
MAX, the database, or the clock.
"""

from __future__ import annotations

from collections.abc import Sequence

from .models import (
    MAX_REASON_CHARS,
    MAX_SCALE,
    MIN_SCALE,
    Question,
    QuestionKind,
    SurveyAnswer,
    SurveyError,
)

MAX_QUESTIONS = 30


def validate_survey(questions: Sequence[Question]) -> None:
    """Reject a survey that cannot be asked: empty, too long, duplicate or self-contradictory."""
    if not questions:
        raise SurveyError("a survey needs at least one question")
    if len(questions) > MAX_QUESTIONS:
        raise SurveyError(f"a survey has at most {MAX_QUESTIONS} questions")
    seen: set[str] = set()
    for question in questions:
        if question.id in seen:
            raise SurveyError(f"duplicate question id {question.id!r}")
        seen.add(question.id)
        question.validate()


def parse_answer(
    question: Question, *, text: str | None = None, option_id: str | None = None
) -> SurveyAnswer:
    """Turn raw input into an answer, or explain why it is not one."""
    match question.kind:
        case QuestionKind.CHOICE:
            return _choice(question, option_id, text)
        case QuestionKind.SCALE:
            return _scale(question, text, option_id)
        case QuestionKind.OPEN:
            return _open(question, text, option_id)


def needs_reason(question: Question, answer: SurveyAnswer) -> bool:
    """A low scale score must be explained; choice and open questions never ask for a reason."""
    if question.kind is not QuestionKind.SCALE:
        return False
    return scale_deficit(question, answer) > 0


def scale_deficit(question: Question, answer: SurveyAnswer) -> int:
    """How far below the comfort threshold a score landed; zero when the score is acceptable."""
    if answer.score is None or question.low_threshold is None:
        return 0
    return max(0, question.low_threshold - answer.score)


def _choice(question: Question, option_id: str | None, text: str | None) -> SurveyAnswer:
    """Accept both a button payload and the option text a person may type instead.

    Live run 2026-10-24: typing "Пока не уверен" under a choice question was rejected as an
    unknown option, so the bot repeated the question and the person had no way to see why.
    """
    known = {option.id for option in question.options}
    chosen = (option_id or (text or "").strip()).strip()
    if not chosen:
        raise SurveyError(f"question {question.id!r}: an option is required")
    if chosen not in known:
        by_text = {
            _normalized(option.text): option.id
            for option in question.options
            if option.text is not None
        }
        matched = by_text.get(_normalized(chosen))
        if matched is None:
            raise SurveyError(
                f"question {question.id!r}: unknown option {chosen!r}, "
                f"expected one of {sorted(known)}"
            )
        chosen = matched
    return SurveyAnswer(question_id=question.id, option_id=chosen)


def _normalized(value: str) -> str:
    return " ".join(value.lower().replace("ё", "е").split())


def _scale(question: Question, text: str | None, option_id: str | None) -> SurveyAnswer:
    raw = (text or option_id or "").strip().replace(",", ".")
    if not raw:
        raise SurveyError(f"question {question.id!r}: a score is required")
    try:
        score = int(raw.split("/")[0].strip())
    except ValueError:
        raise SurveyError(
            f"question {question.id!r}: {raw!r} is not a score from {MIN_SCALE} to {MAX_SCALE}"
        ) from None
    if not MIN_SCALE <= score <= MAX_SCALE:
        raise SurveyError(
            f"question {question.id!r}: score {score} is outside {MIN_SCALE}..{MAX_SCALE}"
        )
    return SurveyAnswer(question_id=question.id, score=score)


def _open(question: Question, text: str | None, option_id: str | None) -> SurveyAnswer:
    if option_id is not None:
        raise SurveyError(f"question {question.id!r}: an open question takes text, not an option")
    cleaned = (text or "").strip()
    if not cleaned:
        raise SurveyError(f"question {question.id!r}: an answer is required")
    if len(cleaned) > MAX_REASON_CHARS:
        raise SurveyError(
            f"question {question.id!r}: answer exceeds {MAX_REASON_CHARS} characters"
        )
    return SurveyAnswer(question_id=question.id, text=cleaned)
