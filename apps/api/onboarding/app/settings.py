"""Typed configuration. The process refuses to start on an invalid configuration.

Secrets are ``SecretStr`` so a stray log call prints ``**********`` instead of the token.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True, slots=True)
class AdminToken:
    """One ``ADMIN_TOKENS`` entry. ``expires_at`` is the first instant the token is invalid."""

    role: str
    subject: str
    expires_at: datetime | None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    environment: Literal["local", "staging", "production"] = "local"
    log_level: str = "INFO"

    max_base_url: str = "https://platform-api2.max.ru"
    max_bot_token: SecretStr = SecretStr("")
    max_webhook_secret: SecretStr = SecretStr("")
    max_ca_bundle: Path | None = None
    max_messages_per_second: float = 2.0
    max_callbacks_enabled: bool = False

    llm_provider: Literal["openai", "gigachat", "extractive"] = "openai"
    llm_profile: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: SecretStr = SecretStr("")
    llm_oauth_url: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    llm_model: str = "gpt-4o-mini"
    # Explicit overrides. ``None`` means "the model profile in apps/api/model-profiles decides".
    llm_max_tokens: int | None = None
    llm_timeout_s: float | None = None
    llm_max_retries: int | None = None
    llm_reasoning_effort: Literal["none", "low", "medium", "high"] | None = None
    llm_breaker_threshold: int = 3
    llm_breaker_cooldown_s: float = 30.0
    llm_price_input_rub_per_1k: float | None = None
    llm_price_output_rub_per_1k: float | None = None
    llm_extra_headers_raw: SecretStr = Field(default=SecretStr(""), alias="LLM_EXTRA_HEADERS")

    embed_provider: Literal["openai", "gigachat", "hashing"] = "hashing"
    embed_profile: str = ""
    embed_base_url: str = ""
    embed_api_key: SecretStr = SecretStr("")
    embed_model: str = "Embeddings"
    embed_dim: int = 1024
    embed_timeout_s: float | None = None
    llm_embed_scope: str = "GIGACHAT_API_PERS"

    rerank_base_url: str = ""
    rerank_profile: str = ""
    rerank_api_key: SecretStr = SecretStr("")
    rerank_model: str = ""
    rerank_timeout_s: float | None = None

    sentiment_provider: Literal["prompt", "jev"] = "prompt"
    jev_base_url: str = "https://api.typesafe.ai/v1"
    jev_api_key: SecretStr = SecretStr("")
    jev_timeout_s: float = 8.0
    jev_max_retries: int = 2

    answer_min_confidence: float = 0.45
    recall_limit: int = 30
    rerank_limit: int = 5
    max_question_chars: int = 1000

    database_url: str = "postgresql+asyncpg://onboarding:onboarding@localhost:5432/onboarding"
    admin_tokens_raw: str = Field(default="", alias="ADMIN_TOKENS")
    admin_page_size: int = 50
    data_retention_days: int = 365

    prompts_dir: Path = Field(default=REPO_ROOT / "docs" / "prompts")
    model_profiles_dir: Path = Field(default=REPO_ROOT / "apps" / "api" / "model-profiles")
    knowledge_dir: Path = Field(default=REPO_ROOT / "knowledge")
    contracts_dir: Path = Field(default=REPO_ROOT / "docs" / "contracts")
    copy_path: Path = Field(default=REPO_ROOT / "docs" / "product" / "copy.yaml")

    @model_validator(mode="after")
    def _check(self) -> Settings:
        self._check_llm()
        self._check_limits()
        self._check_production()
        return self

    def _check_llm(self) -> None:
        """Every knob is optional: ``None`` defers to the selected model profile."""
        if self.llm_timeout_s is not None and self.llm_timeout_s <= 0:
            raise ValueError("LLM_TIMEOUT_S must be positive")
        if self.llm_max_tokens is not None and self.llm_max_tokens <= 0:
            raise ValueError("LLM_MAX_TOKENS must be positive")
        if self.llm_max_retries is not None and self.llm_max_retries < 0:
            raise ValueError("LLM_MAX_RETRIES must not be negative")
        if self.llm_profile and self.llm_provider == "extractive":
            raise ValueError("LLM_PROFILE needs a hosted provider, not extractive")
        if self.rerank_profile and not self.rerank_base_url:
            raise ValueError("RERANK_PROFILE requires RERANK_BASE_URL")
        if self.rerank_base_url and not (self.rerank_model or self.rerank_profile):
            raise ValueError(
                "RERANK_MODEL or RERANK_PROFILE is required when RERANK_BASE_URL is set"
            )
        if self.rerank_timeout_s is not None and self.rerank_timeout_s <= 0:
            raise ValueError("RERANK_TIMEOUT_S must be positive")
        if self.embed_timeout_s is not None and self.embed_timeout_s <= 0:
            raise ValueError("EMBED_TIMEOUT_S must be positive")

    def _check_limits(self) -> None:
        if self.sentiment_provider == "jev" and not self.jev_api_key.get_secret_value():
            raise ValueError("SENTIMENT_PROVIDER=jev requires JEV_API_KEY")
        if not 0.0 <= self.answer_min_confidence <= 1.0:
            raise ValueError("ANSWER_MIN_CONFIDENCE must be within [0, 1]")
        if self.embed_dim < 8:
            raise ValueError("EMBED_DIM must be at least 8")
        if self.recall_limit < self.rerank_limit:
            raise ValueError("RECALL_LIMIT must be at least RERANK_LIMIT")
        if any(char in name for name in self.llm_extra_headers for char in "\r\n"):
            raise ValueError("LLM_EXTRA_HEADERS names must not contain newlines")
        if any(char in value for value in self.llm_extra_headers.values() for char in "\r\n"):
            raise ValueError("LLM_EXTRA_HEADERS values must not contain newlines")
        if self.data_retention_days < 1:
            raise ValueError("DATA_RETENTION_DAYS must be at least 1")

    def _check_production(self) -> None:
        if self.environment != "production":
            return
        if self.llm_provider == "extractive":
            raise ValueError("LLM_PROVIDER=extractive is only for local demos")
        if self.embed_provider == "hashing":
            raise ValueError("EMBED_PROVIDER=hashing is only for local demos")
        missing = [
            name
            for name, value in (
                ("MAX_BOT_TOKEN", self.max_bot_token.get_secret_value()),
                ("MAX_WEBHOOK_SECRET", self.max_webhook_secret.get_secret_value()),
                ("LLM_API_KEY", self.llm_api_key.get_secret_value()),
                ("ADMIN_TOKENS", self.admin_tokens_raw),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"production requires {missing}")

    @property
    def llm_extra_headers(self) -> dict[str, str]:
        """Static headers for an OpenAI-compatible gateway, parsed from a JSON object.

        The raw value is a ``SecretStr`` because a gateway may require a session or tracing token.
        Authentication headers are never overridable from here; the provider owns them.
        """
        raw = self.llm_extra_headers_raw.get_secret_value().strip()
        if not raw:
            return {}
        try:
            value: Any = json.loads(raw)
        except json.JSONDecodeError:
            raise ValueError("LLM_EXTRA_HEADERS must be a JSON object") from None
        if not isinstance(value, dict) or not all(
            isinstance(name, str) and isinstance(header, str) for name, header in value.items()
        ):
            raise ValueError("LLM_EXTRA_HEADERS must be a JSON object of strings")
        forbidden = {"authorization", "content-type", "content-length", "host"}
        if any(
            not name or not name.isascii() or not header.isascii() for name, header in value.items()
        ):
            raise ValueError("LLM_EXTRA_HEADERS names and values must be non-empty ASCII")
        conflict = sorted(name for name in value if name.lower() in forbidden)
        if conflict:
            raise ValueError(f"LLM_EXTRA_HEADERS may not override {conflict}")
        return {str(name): str(header) for name, header in value.items()}

    @property
    def admin_principals(self) -> dict[str, AdminToken]:
        """``ADMIN_TOKENS`` as ``token:role:subject[:YYYY-MM-DD]`` entries.

        ``subject`` is the recruiter id for ``recruiter``, the department for ``manager`` and the
        HR id for ``hr_admin``. The optional date is the last valid day; the token expires at
        00:00 UTC of the next day, so a date is inclusive. A token never carries a wildcard.
        """
        principals: dict[str, AdminToken] = {}
        for raw in self.admin_tokens_raw.split(","):
            entry = raw.strip()
            if not entry:
                continue
            parts = entry.split(":")
            if len(parts) not in {3, 4}:
                raise ValueError(
                    "ADMIN_TOKENS entries must be token:role:subject"
                    " or token:role:subject:YYYY-MM-DD"
                )
            token, role, subject = parts[:3]
            if not token or role not in {"recruiter", "manager", "hr_admin"} or not subject:
                raise ValueError(
                    "ADMIN_TOKENS must be comma-separated token:role:subject entries "
                    "with role recruiter, manager or hr_admin"
                )
            if token in principals:
                raise ValueError("ADMIN_TOKENS contains a duplicate token")
            expires_at: datetime | None = None
            if len(parts) == 4:
                try:
                    last_day = date.fromisoformat(parts[3])
                except ValueError:
                    raise ValueError(
                        "ADMIN_TOKENS expiry must be an ISO date, for example 2026-12-31"
                    ) from None
                expires_at = datetime.combine(last_day + timedelta(days=1), time.min, tzinfo=UTC)
            principals[token] = AdminToken(role=role, subject=subject, expires_at=expires_at)
        return principals

    @property
    def is_llm_configured(self) -> bool:
        if self.llm_provider == "extractive":
            return True
        return bool(self.llm_api_key.get_secret_value()) and bool(
            self.llm_profile or self.llm_model
        )
