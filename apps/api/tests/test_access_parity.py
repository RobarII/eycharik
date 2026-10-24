"""The access rule against an oracle written from the plain-language statement of it.

``core.access`` is the implementation. The oracle below is a second, deliberately naive reading of
the same sentences — "a shared document is visible to anyone", "a department document needs the
department grant", "``hr_only`` is never inherited" — so that a change to the implementation has to
argue with prose, not with itself. The SQL path is held to the same oracle in
``tests/test_integration_db.py``: it needs a database, and this file does not.
"""

from __future__ import annotations

from datetime import date, timedelta

from hypothesis import given
from hypothesis import strategies as st

from onboarding.core.access import (
    EVERYONE,
    HR_ONLY,
    AudienceVisible,
    HrOnlyNotWithheld,
    ValidOn,
    audience_predicates,
    evaluate,
    holds,
    is_valid,
    permits,
    predicates,
    subject_of,
)
from onboarding.core.models import DocId, Document

SCOPES = ["dept:it", "dept:sales", "dept:production"]
AUDIENCES = ["all", "hr_only", *SCOPES]
ON_DATE = date(2026, 10, 24)


def oracle(audience: list[str], viewer: list[str]) -> bool:
    """The rule as it is written in the ADR, in the least clever form available."""
    if not audience:
        return False
    if HR_ONLY in audience and HR_ONLY not in viewer:
        return False
    if EVERYONE in audience:
        return True
    return any(scope in viewer for scope in audience)


audiences = st.lists(st.sampled_from(AUDIENCES), min_size=0, max_size=3, unique=True)
viewers = st.lists(st.sampled_from(AUDIENCES), min_size=0, max_size=3, unique=True)


@given(audiences, viewers)
def test_permits_agrees_with_the_stated_rule(audience: list[str], viewer: list[str]) -> None:
    assert permits(audience, viewer) is oracle(audience, viewer)


@given(audiences, viewers)
def test_the_conjunction_agrees_with_permits(audience: list[str], viewer: list[str]) -> None:
    """``permits`` is a thin reader of the conjunction; if the two part, one of them is a copy."""
    subject = subject_of(
        Document(
            id=DocId("hr/test"),
            title="Test",
            text="body",
            audience=tuple(audience),
            valid_from=date(2020, 1, 1),
        )
    )
    assert permits(audience, viewer) is holds(audience_predicates(viewer), subject)


@given(audiences, viewers)
def test_the_shared_arm_is_the_only_one_that_ignores_the_viewer(
    audience: list[str], viewer: list[str]
) -> None:
    subject = subject_of(
        Document(
            id=DocId("hr/test"),
            title="Test",
            text="body",
            audience=tuple(audience),
            valid_from=date(2020, 1, 1),
        )
    )
    visible = evaluate(AudienceVisible(tuple(viewer)), subject)
    assert visible is (EVERYONE in audience or bool(set(audience) & set(viewer)))


@given(audiences, st.booleans())
def test_the_hr_arm_only_ever_narrows(audience: list[str], granted: bool) -> None:
    subject = subject_of(
        Document(
            id=DocId("hr/test"),
            title="Test",
            text="body",
            audience=tuple(audience),
            valid_from=date(2020, 1, 1),
        )
    )
    assert evaluate(HrOnlyNotWithheld(granted), subject) is (
        granted or HR_ONLY not in audience
    )


@given(st.integers(min_value=-400, max_value=400), st.integers(min_value=0, max_value=400))
def test_validity_is_half_open_on_both_edges(offset: int, length: int) -> None:
    """``valid_from <= on_date <= valid_to``; an expired edition is invisible to everyone."""
    start = ON_DATE + timedelta(days=offset)
    end = start + timedelta(days=length) if length else None
    document = Document(
        id=DocId("hr/test"),
        title="Test",
        text="body",
        audience=("all",),
        valid_from=start,
        valid_to=end,
    )
    expected = start <= ON_DATE and (end is None or end >= ON_DATE)
    assert is_valid(document, ON_DATE) is expected
    assert evaluate(ValidOn(ON_DATE), subject_of(document)) is expected


def test_the_whole_filter_refuses_an_inactive_document() -> None:
    """``Active`` is the one predicate the memory backend can never satisfy on its own path."""
    document = Document(
        id=DocId("hr/test"),
        title="Test",
        text="body",
        audience=("all",),
        valid_from=date(2020, 1, 1),
    )
    assert holds(predicates(["all"], ON_DATE), subject_of(document)) is True
    assert holds(predicates(["all"], ON_DATE), subject_of(document, status="draft")) is False
