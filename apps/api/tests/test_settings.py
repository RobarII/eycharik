from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from onboarding.app.settings import Settings


def test_admin_principals_parse_role_and_subject() -> None:
    settings = Settings(
        _env_file=None,
        admin_tokens_raw="alpha:recruiter:rec-1,beta:hr_admin:hr-1",
    )

    assert set(settings.admin_principals) == {"alpha", "beta"}
    assert settings.admin_principals["alpha"].role == "recruiter"
    assert settings.admin_principals["alpha"].subject == "rec-1"
    assert settings.admin_principals["beta"].role == "hr_admin"
    assert settings.admin_principals["beta"].expires_at is None


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


def test_production_requires_a_metrics_token() -> None:
    with pytest.raises(ValidationError, match="METRICS_TOKEN"):
        Settings(
            _env_file=None,
            environment="production",
            max_bot_token="bot",
            max_webhook_secret="secret",
            llm_api_key="key",
            embed_provider="gigachat",
            admin_tokens_raw="token:hr_admin:hr-1",
            metrics_token="",
        )


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


def test_a_decisions_provider_without_a_key_is_refused_at_startup() -> None:
    with pytest.raises(ValidationError, match="CLASSIFY_API_KEY"):
        Settings(_env_file=None, sentiment_provider="decisions")


def test_the_classifier_default_resolves_at_runtime_not_in_configuration() -> None:
    """``auto`` names a rule, so an offline profile starts without a key and claims no provider."""

    assert Settings(_env_file=None).sentiment_provider == "auto"
    configured = Settings(_env_file=None, sentiment_provider="decisions", classify_api_key="k")
    assert configured.classify_api_key


def test_the_old_jev_names_still_configure_the_decisions_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A `.env` written before the rename must not fall back to the keyword floor silently."""

    monkeypatch.setenv("JEV_API_KEY", "legacy-key")
    monkeypatch.setenv("JEV_BASE_URL", "https://legacy.example/v1")
    legacy = Settings(_env_file=None)
    assert legacy.classify_api_key.get_secret_value() == "legacy-key"
    assert legacy.classify_base_url == "https://legacy.example/v1"

    monkeypatch.setenv("CLASSIFY_API_KEY", "new-key")
    assert Settings(_env_file=None).classify_api_key.get_secret_value() == "new-key"


def test_a_rubric_selector_must_be_named_and_versioned() -> None:
    with pytest.raises(ValidationError, match="SENTIMENT_RUBRIC"):
        Settings(_env_file=None, sentiment_rubric="sentiment-jev")

    assert Settings(_env_file=None, sentiment_rubric="sentiment-jev@2").sentiment_rubric


def test_a_classify_profile_name_cannot_escape_the_profiles_directory() -> None:
    with pytest.raises(ValidationError, match="CLASSIFY_PROFILE"):
        Settings(_env_file=None, classify_profile="../etc/passwd")


def test_a_negative_classify_retry_count_is_refused() -> None:
    with pytest.raises(ValidationError, match="CLASSIFY_MAX_RETRIES"):
        Settings(_env_file=None, classify_max_retries=-1)


def test_manager_token_is_supported() -> None:
    principals = Settings(
        _env_file=None, admin_tokens_raw="m-token:manager:ИТ"
    ).admin_principals

    assert principals["m-token"].role == "manager"
    assert principals["m-token"].subject == "ИТ"
    assert principals["m-token"].expires_at is None


def test_token_expiry_is_the_day_after_the_last_valid_day() -> None:
    principals = Settings(
        _env_file=None, admin_tokens_raw="t:recruiter:rec-1:2030-12-31"
    ).admin_principals

    assert principals["t"].expires_at == datetime(2031, 1, 1, tzinfo=UTC)


def test_bad_token_expiry_is_refused() -> None:
    with pytest.raises(ValueError, match="ISO date"):
        _ = Settings(
            _env_file=None, admin_tokens_raw="t:recruiter:rec-1:31.12.2030"
        ).admin_principals


def test_duplicate_tokens_are_refused() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        _ = Settings(
            _env_file=None,
            admin_tokens_raw="t:recruiter:rec-1,t:hr_admin:hr-1",
        ).admin_principals


def test_retention_window_must_be_positive() -> None:
    with pytest.raises(ValidationError, match="DATA_RETENTION_DAYS"):
        Settings(_env_file=None, data_retention_days=0)


def test_the_local_env_file_wins_over_the_shared_one(tmp_path: Path) -> None:
    """`.env.local` is the developer's secrets file; a stray `.env` must not redirect it.

    Both files are ignored by git, so the precedence is the only thing standing between a local
    configuration and a silently offline run.
    """
    (tmp_path / ".env").write_text("LLM_PROVIDER=extractive\nEMBED_PROVIDER=hashing\n")
    (tmp_path / ".env.local").write_text("LLM_PROVIDER=openai\nEMBED_PROVIDER=openai\n")

    settings = Settings(_env_file=(tmp_path / ".env", tmp_path / ".env.local"))

    assert settings.llm_provider == "openai"
    assert settings.embed_provider == "openai"
