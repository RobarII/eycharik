from __future__ import annotations

from onboarding.core.query import expand_query


def test_a_formal_gift_question_gets_the_corpus_vocabulary() -> None:
    expanded = expand_query("Каковы допустимые рамки бюджета на корпоративные презенты?")

    assert expanded.startswith("Каковы допустимые рамки бюджета на корпоративные презенты?")
    assert "деловой подарок" in expanded
    assert "представительские расходы" in expanded


def test_the_original_question_is_unchanged_when_no_synonym_matches() -> None:
    question = "Сколько дней отпуска положено в первый год?"

    assert expand_query(question) == question


def test_a_presentation_is_not_a_gift() -> None:
    question = "Как подготовить презентацию проекта?"

    assert expand_query(question) == question


def test_mentor_questions_get_onboarding_vocabulary() -> None:
    expanded = expand_query("Что делает наставник?")

    assert expanded.startswith("Что делает наставник?")
    assert "адаптация" in expanded
    assert "испытательный срок" in expanded
