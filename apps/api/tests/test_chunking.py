from __future__ import annotations

from datetime import date

import pytest

from onboarding.core.chunking import split_document
from onboarding.core.models import DocId, Document

DOC = Document(
    id=DocId("hr/leave-policy"),
    title="Отпуска",
    text=(
        "Ежегодный оплачиваемый отпуск — 28 календарных дней. "
        "Право на отпуск возникает после шести месяцев работы.\n\n"
        "Заявление подаётся за 14 дней. Согласование — руководитель, затем HR."
    ),
    audience=("all",),
    valid_from=date(2026, 1, 1),
)


def test_ids_are_stable_across_runs() -> None:
    first = split_document(DOC, max_chars=80, overlap_chars=0)
    second = split_document(DOC, max_chars=80, overlap_chars=0)

    assert [chunk.id for chunk in first] == [chunk.id for chunk in second]
    assert all(chunk.id.startswith("hr/leave-policy#") for chunk in first)


def test_respects_the_character_budget() -> None:
    chunks = split_document(DOC, max_chars=80, overlap_chars=0)

    assert len(chunks) > 1
    assert all(len(chunk.text) <= 80 for chunk in chunks)


def test_no_information_is_lost_without_overlap() -> None:
    chunks = split_document(DOC, max_chars=80, overlap_chars=0)
    joined = " ".join(chunk.text for chunk in chunks)

    assert "28 календарных дней" in joined
    assert "за 14 дней" in joined


def test_overlap_repeats_the_tail() -> None:
    chunks = split_document(DOC, max_chars=90, overlap_chars=40)
    tails = [chunk.text for chunk in chunks[1:]]

    assert any(chunks[0].text.split(". ")[-1].strip(".") in tail for tail in tails)


def test_empty_document_has_no_chunks() -> None:
    empty = Document(
        id=DocId("empty"),
        title="Пусто",
        text="   \n\n ",
        audience=("all",),
        valid_from=date(2026, 1, 1),
    )

    assert split_document(empty) == ()


def test_rejects_invalid_windows() -> None:
    with pytest.raises(ValueError, match="max_chars"):
        split_document(DOC, max_chars=0)
    with pytest.raises(ValueError, match="overlap_chars"):
        split_document(DOC, max_chars=100, overlap_chars=100)
