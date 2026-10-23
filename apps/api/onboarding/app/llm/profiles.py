"""Model profiles: what to call, how to shape the request, and what it costs.

A profile is one YAML file validated against ``docs/contracts/model-profile.schema.json``. The
gateway, the embedder, and the reranker read a profile; none of them branches on a model name. A new
model is a new file plus an eval run, never a code change (ADR 0013).

Resolution order for every knob: an explicit environment value, then the profile, then the dataclass
default. Environment stays the deployment's business (base URL, key, breaker); the profile owns the
model's own envelope and capabilities.
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal, cast

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from onboarding.app.settings import Settings
from onboarding.ports import AnswerProfile, EmbeddingProfile, RerankProfile

Role = Literal["answer", "embed", "rerank"]

MAX_PROFILE_BYTES = 8_000
_NAME = re.compile(r"[a-z0-9][a-z0-9._-]*")

# Dataclass fields with ``slots=True`` are descriptors, so defaults are read from instances.
_ANSWER = AnswerProfile(name="default", model="default")
_EMBED = EmbeddingProfile(name="default", model="default")
_RERANK = RerankProfile(name="default", model="default")

_EMBED_FAMILY: dict[str, str] = {
    "hashing": "local",
    "gigachat": "gigachat",
    "openai": "openai-chat",
}


class ProfileError(ValueError):
    """The profile file is missing, oversized, or violates its contract."""


class ProfileLibrary:
    """Read profile files once and cache them. I/O lives here, never in the gateway."""

    def __init__(self, root: Path, schema_path: Path) -> None:
        self._root = root
        self._schema_path = schema_path
        self._validators: dict[str, Draft202012Validator] = {}
        self._cache: dict[tuple[str, str], dict[str, Any]] = {}

    def answer(self, name: str) -> AnswerProfile:
        return _answer(self.raw("answer", name))

    def embed(self, name: str) -> EmbeddingProfile:
        return _embedding(self.raw("embed", name))

    def rerank(self, name: str) -> RerankProfile:
        return _rerank(self.raw("rerank", name))

    def available(self, role: Role) -> tuple[str, ...]:
        directory = self._root / role
        if not directory.is_dir():
            return ()
        return tuple(sorted(path.stem for path in directory.glob("*.yaml")))

    def raw(self, role: Role, name: str) -> dict[str, Any]:
        key = (role, name)
        if key not in self._cache:
            self._cache[key] = self._read(role, name)
        return self._cache[key]

    def _read(self, role: Role, name: str) -> dict[str, Any]:
        if not _NAME.fullmatch(name):
            raise ProfileError(f"invalid model profile name {name!r}")
        path = self._root / role / f"{name}.yaml"
        if not path.is_file():
            known = ", ".join(self.available(role)) or "none"
            raise ProfileError(f"missing model profile {path} (known {role} profiles: {known})")
        if path.stat().st_size > MAX_PROFILE_BYTES:
            raise ProfileError(f"{path} exceeds {MAX_PROFILE_BYTES} bytes")
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            raise ProfileError(f"{path}: not valid YAML: {error}") from None
        if not isinstance(data, dict):
            raise ProfileError(f"{path}: expected a mapping")
        if data.get("role") != role:
            raise ProfileError(
                f"{path}: role is {data.get('role')!r}, but the file lives under {role}/"
            )
        failures = sorted(
            self._validator(role).iter_errors(data), key=lambda failure: list(failure.path)
        )
        if failures:
            failure = failures[0]
            where = "/".join(str(part) for part in failure.path) or "profile"
            raise ProfileError(f"{path}: {where}: {failure.message}")
        return data

    def _validator(self, role: Role) -> Draft202012Validator:
        """Validate against the branch for this role, so errors name the field, not ``oneOf``."""
        if role not in self._validators:
            schema: Any = json.loads(self._schema_path.read_text(encoding="utf-8"))
            branch = next(
                (
                    candidate
                    for candidate in schema.get("oneOf", [])
                    if candidate.get("properties", {}).get("role", {}).get("const") == role
                ),
                None,
            )
            if branch is None:
                raise ProfileError(f"{self._schema_path}: no schema branch for role {role!r}")
            self._validators[role] = Draft202012Validator(
                {**branch, "$defs": schema.get("$defs", {})}, format_checker=FormatChecker()
            )
        return self._validators[role]


def library(settings: Settings) -> ProfileLibrary:
    return ProfileLibrary(
        settings.model_profiles_dir,
        settings.contracts_dir / "model-profile.schema.json",
    )


def answer_profile(settings: Settings) -> AnswerProfile:
    """The configured answer model, with explicit environment overrides applied on top."""
    if settings.llm_profile:
        profile = library(settings).answer(settings.llm_profile)
        return replace(
            profile,
            max_tokens=_env_int(settings.llm_max_tokens, profile.max_tokens),
            timeout_s=_env_float(settings.llm_timeout_s, profile.timeout_s),
            max_retries=_env_int(settings.llm_max_retries, profile.max_retries),
            reasoning_effort=settings.llm_reasoning_effort or profile.reasoning_effort,
            price_input_rub_per_1k=_env_float(
                settings.llm_price_input_rub_per_1k, profile.price_input_rub_per_1k
            ),
            price_output_rub_per_1k=_env_float(
                settings.llm_price_output_rub_per_1k, profile.price_output_rub_per_1k
            ),
        )
    return AnswerProfile(
        name="env",
        model=settings.llm_model,
        family="gigachat" if settings.llm_provider == "gigachat" else "openai-chat",
        reasoning_effort=settings.llm_reasoning_effort,
        max_tokens=_env_int(settings.llm_max_tokens, _ANSWER.max_tokens),
        timeout_s=_env_float(settings.llm_timeout_s, _ANSWER.timeout_s),
        max_retries=_env_int(settings.llm_max_retries, _ANSWER.max_retries),
        price_input_rub_per_1k=_env_float(settings.llm_price_input_rub_per_1k, 0.0),
        price_output_rub_per_1k=_env_float(settings.llm_price_output_rub_per_1k, 0.0),
    )


def embedding_profile(settings: Settings) -> EmbeddingProfile:
    """The configured embedder. A profile makes the vector width explicit before any request."""
    if settings.embed_profile:
        profile = library(settings).embed(settings.embed_profile)
        if "embed_dim" in settings.model_fields_set and settings.embed_dim != profile.dim:
            raise ProfileError(
                f"EMBED_DIM is {settings.embed_dim}, but profile {profile.name!r} declares "
                f"dim {profile.dim}; a wider vector is a migration, not a setting"
            )
        return replace(profile, timeout_s=_env_float(settings.embed_timeout_s, profile.timeout_s))
    family = _EMBED_FAMILY[settings.embed_provider]
    return EmbeddingProfile(
        name="env",
        model=settings.embed_model,
        family=cast(Any, family),
        dim=settings.embed_dim,
        timeout_s=_env_float(settings.embed_timeout_s, _EMBED.timeout_s),
    )


def rerank_profile(settings: Settings) -> RerankProfile | None:
    """``None`` when the stage is disabled: no base URL, no reranker, no ranking change."""
    if not settings.rerank_base_url:
        return None
    if settings.rerank_profile:
        profile = library(settings).rerank(settings.rerank_profile)
        return replace(
            profile, timeout_s=_env_float(settings.rerank_timeout_s, profile.timeout_s)
        )
    if not settings.rerank_model:
        raise ProfileError("RERANK_MODEL or RERANK_PROFILE is required when RERANK_BASE_URL is set")
    return RerankProfile(
        name="env",
        model=settings.rerank_model,
        timeout_s=_env_float(settings.rerank_timeout_s, _RERANK.timeout_s),
    )


def _answer(data: dict[str, Any]) -> AnswerProfile:
    return AnswerProfile(
        name=_text(data, "name"),
        model=_text(data, "model"),
        family=_family(data, ("openai-chat", "gigachat"), "openai-chat"),
        json_mode=_flag(data, "json_mode", default=True),
        max_tokens_field=_text_default(data, "max_tokens_field", "max_tokens"),
        reasoning_effort=_text_or_none(data, "reasoning_effort"),
        temperature=_number(data, "temperature", _ANSWER.temperature),
        max_tokens=_integer(data, "max_tokens", _ANSWER.max_tokens),
        timeout_s=_number(data, "timeout_s", _ANSWER.timeout_s),
        max_retries=_integer(data, "max_retries", _ANSWER.max_retries),
        retry_empty_completion=_flag(data, "retry_empty_completion", default=True),
        price_input_rub_per_1k=_number(data, "price_input_rub_per_1k", 0.0),
        price_output_rub_per_1k=_number(data, "price_output_rub_per_1k", 0.0),
    )


def _embedding(data: dict[str, Any]) -> EmbeddingProfile:
    return EmbeddingProfile(
        name=_text(data, "name"),
        model=_text(data, "model"),
        family=_family(data, ("openai-chat", "gigachat", "local"), "openai-chat"),
        dim=_integer(data, "dim", _EMBED.dim),
        timeout_s=_number(data, "timeout_s", _EMBED.timeout_s),
    )


def _rerank(data: dict[str, Any]) -> RerankProfile:
    return RerankProfile(
        name=_text(data, "name"),
        model=_text(data, "model"),
        family=_family(data, ("cohere-rerank",), "cohere-rerank"),
        timeout_s=_number(data, "timeout_s", _RERANK.timeout_s),
    )


def _text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ProfileError(f"{key} must be a non-empty string")
    return value


def _text_default(data: dict[str, Any], key: str, default: str) -> str:
    if key not in data:
        return default
    return _text(data, key)


def _text_or_none(data: dict[str, Any], key: str) -> str | None:
    if key not in data or data[key] is None:
        return None
    return _text(data, key)


def _family(data: dict[str, Any], allowed: tuple[str, ...], default: str) -> Any:
    value = data.get("family", default)
    if value not in allowed:
        raise ProfileError(f"family must be one of {allowed}, got {value!r}")
    return value


def _number(data: dict[str, Any], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ProfileError(f"{key} must be a number")
    return float(value)


def _integer(data: dict[str, Any], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProfileError(f"{key} must be an integer")
    return value


def _flag(data: dict[str, Any], key: str, *, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ProfileError(f"{key} must be a boolean")
    return value


def _env_float(value: float | None, fallback: float) -> float:
    """An explicit environment value wins; otherwise the profile or the dataclass default."""
    return fallback if value is None else value


def _env_int(value: int | None, fallback: int) -> int:
    return fallback if value is None else value
