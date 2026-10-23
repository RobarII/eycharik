from __future__ import annotations

from datetime import date

from onboarding.core.access import is_valid, permits
from onboarding.core.models import DocId, Document


def document(valid_from: date, valid_to: date | None) -> Document:
    return Document(
        id=DocId("hr/test"),
        title="Test",
        text="body",
        audience=("all",),
        valid_from=valid_from,
        valid_to=valid_to,
    )


def test_everyone_scope_is_open() -> None:
    assert permits(["all"], [])
    assert permits(["all"], ["dept:it"])


def test_department_scope_requires_a_match() -> None:
    assert permits(["dept:it"], ["dept:it"])
    assert not permits(["dept:it"], ["dept:sales"])
    assert not permits(["dept:it"], [])


def test_hr_only_is_never_inherited_from_all() -> None:
    assert not permits(["hr_only"], ["all"])
    assert permits(["hr_only"], ["hr_only"])


def test_empty_audience_is_closed() -> None:
    assert not permits([], ["all"])


def test_validity_window() -> None:
    current = document(date(2026, 1, 1), None)

    assert not is_valid(current, date(2025, 12, 31))
    assert is_valid(current, date(2026, 1, 1))
    assert is_valid(current, date(2030, 1, 1))


def test_expired_document_is_invalid() -> None:
    expired = document(date(2024, 1, 1), date(2025, 1, 1))

    assert is_valid(expired, date(2025, 1, 1))
    assert not is_valid(expired, date(2025, 1, 2))
