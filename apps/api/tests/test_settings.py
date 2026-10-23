from __future__ import annotations

import pytest
from pydantic import ValidationError

from onboarding.app.settings import Settings


def test_admin_principals_parse_role_and_subject() -> None:
    settings = Settings(
        _env_file=None,
        admin_tokens_raw="alpha:recruiter:rec-1,beta:hr_admin:hr-1",
    )

    assert settings.admin_principals == {
        "alpha": ("recruiter", "rec-1"),
        "beta": ("hr_admin", "hr-1"),
    }


@pytest.mark.parametrize(
    "raw",
    ["alpha:recruiter", "alpha:admin:rec-1", ":recruiter:rec-1", "alpha:recruiter:"],
)
def test_bad_admin_tokens_are_rejected(raw: str) -> None:
    settings = Settings(_env_file=None, admin_tokens_raw=raw)

    with pytest.raises(ValueError, match="ADMIN_TOKENS"):
        _ = settings.admin_principals


def test_production_requires_secrets() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production")


def test_recall_must_not_be_smaller_than_rerank() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, recall_limit=3, rerank_limit=5)


def test_confidence_is_bounded() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, answer_min_confidence=1.5)
