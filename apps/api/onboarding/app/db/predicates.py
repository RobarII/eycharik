"""Compile the retrieval rule into SQL.

``core.access`` owns the rule; this module knows only how to say each of its four conditions in
Postgres. One branch per predicate kind, no fallback: ``match`` over the union means mypy refuses a
predicate that has no SQL, so the two paths cannot drift apart silently. The in-memory path and
this one are held to the same answers by ``tests/test_access_parity.py`` and, on a real database, by
the ACL parity test in ``tests/test_integration_db.py``.
"""

from __future__ import annotations

import typing
from collections.abc import Sequence
from datetime import date

from sqlalchemy import ColumnElement, Text, and_, cast, not_, or_, true
from sqlalchemy.dialects.postgresql import ARRAY

from onboarding.app.db.models import DocumentRow
from onboarding.core.access import (
    EVERYONE,
    HR_ONLY,
    Active,
    AudienceVisible,
    HrOnlyNotWithheld,
    Predicate,
    ValidOn,
)
from onboarding.core.access import (
    predicates as acl_predicates,
)


def compile_predicate(predicate: Predicate) -> ColumnElement[bool]:
    """One condition, one SQL fragment. The shapes mirror ``core.access.evaluate`` line by line."""
    match predicate:
        case Active():
            return DocumentRow.status == "active"
        case ValidOn(on_date):
            return or_(
                DocumentRow.valid_from.is_(None),
                DocumentRow.valid_from <= on_date,
            ) & or_(
                DocumentRow.valid_to.is_(None),
                DocumentRow.valid_to >= on_date,
            )
        case AudienceVisible(grants):
            # ``all`` means everyone, so a shared document matches even a viewer whose scopes name
            # no grant. The second arm asks the JSONB audience array for any of the grants.
            return or_(
                DocumentRow.audience.op("?")(EVERYONE),
                DocumentRow.audience.op("?|")(cast(list(grants), ARRAY(Text))),
            )
        case HrOnlyNotWithheld(granted):
            if granted:
                # The viewer holds the grant, so this arm cannot refuse anything. SQLAlchemy types
                # ``true()`` as ``Any``; the cast states what the SQL already says.
                return typing.cast("ColumnElement[bool]", true())
            withholds: ColumnElement[bool] = DocumentRow.audience.op("?")(HR_ONLY)
            return not_(withholds)
    raise AssertionError(f"uncompiled predicate: {predicate!r}")


def compile_predicates(predicates: Sequence[Predicate]) -> ColumnElement[bool]:
    return and_(*[compile_predicate(predicate) for predicate in predicates])


def acl_clause(viewer: Sequence[str], on_date: date) -> ColumnElement[bool]:
    """The whole filter for one viewer on one date, from the one rule in ``core.access``."""
    return compile_predicates(acl_predicates(viewer, on_date))
