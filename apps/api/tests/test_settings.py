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


def test_extra_headers_come_from_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_EXTRA_HEADERS", '{"x-opencode-session": "secret-session"}')

    settings = Settings(_env_file=None)

    assert settings.llm_extra_headers == {"x-opencode-session": "secret-session"}
    assert "secret-session" not in repr(settings)


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        '["x"]',
        '{"authorization": "Bearer stolen"}',
        '{"x-test": "line\\nbreak"}',
        '{"x-test": "кириллица"}',
        '{"": "empty"}',
    ],
)
def test_bad_extra_headers_are_rejected(raw: str) -> None:
    with pytest.raises(ValueError, match="LLM_EXTRA_HEADERS"):
        _ = Settings(_env_file=None, llm_extra_headers_raw=raw).llm_extra_headers


def test_max_tokens_must_be_positive() -> None:
    with pytest.raises(ValidationError, match="LLM_MAX_TOKENS"):
        Settings(_env_file=None, llm_max_tokens=0)


def test_production_requires_secrets() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production")


def test_recall_must_not_be_smaller_than_rerank() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, recall_limit=3, rerank_limit=5)


def test_confidence_is_bounded() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, answer_min_confidence=1.5)


def test_production_rejects_the_offline_llm() -> None:
    with pytest.raises(ValidationError, match="extractive"):
        Settings(_env_file=None, environment="production", llm_provider="extractive")


def test_production_rejects_hashing_embeddings() -> None:
    with pytest.raises(ValidationError, match="hashing"):
        Settings(_env_file=None, environment="production", embed_provider="hashing")
