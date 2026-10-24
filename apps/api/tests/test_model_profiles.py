"""Model profiles: the contract is the schema, and the loader refuses a file that breaks it."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from onboarding.app.clock import FrozenClock
from onboarding.app.llm.gateway import GatewayLLM, build_llm
from onboarding.app.llm.profiles import (
    ProfileError,
    ProfileLibrary,
    answer_profile,
    classify_profile,
    embedding_profile,
    personal_data_contour,
    rerank_profile,
)
from onboarding.app.settings import REPO_ROOT, Settings

from .conftest import NOW

CONTRACTS = REPO_ROOT / "docs" / "contracts"
SHIPPED = REPO_ROOT / "apps" / "api" / "model-profiles"


def settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]


def write_profile(root: Path, role: str, name: str, body: str) -> Path:
    directory = root / role
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_every_shipped_profile_satisfies_the_contract() -> None:
    library = ProfileLibrary(SHIPPED, CONTRACTS / "model-profile.schema.json")

    for role in ("answer", "embed", "rerank", "classify"):
        names = library.available(role)
        assert names, f"no {role} profiles"
        for name in names:
            loaded = library.raw(role, name)
            assert loaded["name"] == name
            assert loaded["role"] == role


def test_shipped_profiles_load_into_typed_values() -> None:
    library = ProfileLibrary(SHIPPED, CONTRACTS / "model-profile.schema.json")

    answer = library.answer("opencode-deepseek-v4.1-flash")
    assert answer.family == "openai-chat"
    assert answer.model == "deepseek-v4.1-flash"
    assert answer.json_mode

    embed = library.embed("openrouter-qwen3-embedding-8b")
    assert embed.dim == 1024

    rerank = library.rerank("openrouter-cohere-rerank-v3.5")
    assert rerank.model == "cohere/rerank-v3.5"

    classify = library.classify("jev-1.13.0")
    assert classify.family == "typesafe-jev"
    assert classify.rubric == "sentiment-jev@1"


def test_an_unknown_field_is_rejected(tmp_path: Path) -> None:
    write_profile(
        tmp_path,
        "answer",
        "extra",
        "name: extra\nrole: answer\nmodel: m\nturbo: true\n",
    )
    library = ProfileLibrary(tmp_path, CONTRACTS / "model-profile.schema.json")

    with pytest.raises(ProfileError, match="Additional properties"):
        library.answer("extra")


def test_a_profile_in_the_wrong_directory_is_rejected(tmp_path: Path) -> None:
    write_profile(
        tmp_path,
        "answer",
        "misfiled",
        "name: misfiled\nrole: embed\nmodel: m\ndim: 1024\n",
    )
    library = ProfileLibrary(tmp_path, CONTRACTS / "model-profile.schema.json")

    with pytest.raises(ProfileError, match="lives under answer/"):
        library.answer("misfiled")


def test_an_embedding_profile_requires_a_dimension(tmp_path: Path) -> None:
    write_profile(tmp_path, "embed", "wide", "name: wide\nrole: embed\nmodel: m\n")
    library = ProfileLibrary(tmp_path, CONTRACTS / "model-profile.schema.json")

    with pytest.raises(ProfileError, match="dim"):
        library.embed("wide")


def test_a_rerank_profile_rejects_generation_fields(tmp_path: Path) -> None:
    write_profile(
        tmp_path,
        "rerank",
        "noisy",
        "name: noisy\nrole: rerank\nmodel: m\ntemperature: 0.2\n",
    )
    library = ProfileLibrary(tmp_path, CONTRACTS / "model-profile.schema.json")

    with pytest.raises(ProfileError, match="temperature"):
        library.rerank("noisy")


def test_a_classify_profile_needs_a_rubric(tmp_path: Path) -> None:
    write_profile(tmp_path, "classify", "bare", "name: bare\nrole: classify\nmodel: m\n")
    library = ProfileLibrary(tmp_path, CONTRACTS / "model-profile.schema.json")

    with pytest.raises(ProfileError, match="rubric"):
        library.classify("bare")


def test_a_classify_profile_rejects_a_chat_field(tmp_path: Path) -> None:
    write_profile(
        tmp_path,
        "classify",
        "chatty",
        "name: chatty\nrole: classify\nmodel: m\nrubric: sentiment-jev@1\ntemperature: 0.2\n",
    )
    library = ProfileLibrary(tmp_path, CONTRACTS / "model-profile.schema.json")

    with pytest.raises(ProfileError, match="temperature"):
        library.classify("chatty")


def test_a_classify_profile_rejects_a_rubric_without_a_version(tmp_path: Path) -> None:
    write_profile(
        tmp_path,
        "classify",
        "unversioned",
        "name: unversioned\nrole: classify\nmodel: m\nrubric: sentiment-jev\n",
    )
    library = ProfileLibrary(tmp_path, CONTRACTS / "model-profile.schema.json")

    with pytest.raises(ProfileError, match="rubric"):
        library.classify("unversioned")


def test_a_classifier_without_a_profile_is_refused() -> None:
    with pytest.raises(ProfileError, match="CLASSIFY_PROFILE"):
        classify_profile(settings(classify_profile=""))


def test_a_missing_profile_names_the_known_ones() -> None:
    library = ProfileLibrary(SHIPPED, CONTRACTS / "model-profile.schema.json")

    with pytest.raises(ProfileError, match="gigachat-2-pro"):
        library.answer("does-not-exist")


@pytest.mark.parametrize("name", ["../answer/gigachat-2-pro", "GigaChat", ""])
def test_a_name_cannot_escape_the_profiles_directory(name: str) -> None:
    library = ProfileLibrary(SHIPPED, CONTRACTS / "model-profile.schema.json")

    with pytest.raises(ProfileError):
        library.answer(name)


def test_an_answer_model_without_a_profile_is_refused() -> None:
    with pytest.raises(ProfileError, match="LLM_PROFILE"):
        answer_profile(settings(llm_profile=""))


def test_the_environment_overrides_the_selected_profile() -> None:
    profile = answer_profile(
        settings(
            llm_profile="gigachat-2-pro",
            llm_max_tokens=123,
            llm_timeout_s=4.5,
            llm_reasoning_effort="low",
        )
    )

    assert profile.name == "gigachat-2-pro"
    assert profile.model == "GigaChat-2-Pro"
    assert profile.max_tokens == 123
    assert profile.timeout_s == 4.5
    assert profile.reasoning_effort == "low"


def test_the_profile_owns_defaults_the_environment_does_not_set() -> None:
    profile = answer_profile(settings(llm_profile="opencode-deepseek-v4.1-flash"))

    # 1600 leaves room for reasoning inside the same budget: 700 returned empty completions live.
    assert profile.max_tokens == 1600
    assert profile.timeout_s == 30.0
    assert profile.max_retries == 1


def test_a_profile_vector_width_that_contradicts_embed_dim_is_rejected() -> None:
    configured = settings(embed_profile="openrouter-qwen3-embedding-8b", embed_dim=768)

    with pytest.raises(ProfileError, match="migration"):
        embedding_profile(configured)


def test_an_embedding_profile_matching_embed_dim_is_accepted() -> None:
    profile = embedding_profile(settings(embed_profile="local-hashing", embed_dim=1024))

    assert profile.family == "local"
    assert profile.dim == 1024


def test_an_unknown_profile_fails_at_startup() -> None:
    with pytest.raises(ProfileError, match="missing model profile"):
        answer_profile(settings(llm_profile="no-such-model"))


def test_a_rerank_profile_needs_a_base_url() -> None:
    with pytest.raises(ValueError, match="RERANK_BASE_URL"):
        settings(rerank_profile="openrouter-cohere-rerank-v3.5")


def test_rerank_is_disabled_without_a_base_url() -> None:
    assert rerank_profile(settings()) is None


def test_rerank_uses_the_profile_model() -> None:
    profile = rerank_profile(
        settings(
            rerank_base_url="https://rerank.test/v1",
            rerank_profile="openrouter-cohere-rerank-v3.5",
        )
    )

    assert profile is not None
    assert profile.model == "cohere/rerank-v3.5"
    assert profile.timeout_s == 3.0


async def test_build_llm_wires_the_selected_profile() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200)))
    try:
        llm = build_llm(
            settings(llm_profile="opencode-deepseek-v4.1-flash", llm_api_key="sk-test"),
            FrozenClock(NOW),
            client,
        )
    finally:
        await client.aclose()

    assert isinstance(llm, GatewayLLM)
    assert llm.profile.name == "opencode-deepseek-v4.1-flash"
    assert llm.profile.model == "deepseek-v4.1-flash"


def test_a_demo_gateway_is_outside_the_personal_data_contour() -> None:
    """ADR 0030: OpenRouter and OpenCode stay out of the contour that may touch employee data."""
    assert (
        personal_data_contour(
            settings(
                llm_provider="openai",
                llm_profile="openrouter-gpt-4.1-mini",
                embed_provider="openai",
                embed_profile="openrouter-qwen3-embedding-8b",
                rerank_base_url="https://openrouter.ai/api/v1",
                rerank_profile="openrouter-nemotron-rerank-8b",
            )
        )
        is False
    )


def test_a_russian_hosted_stack_is_inside_the_contour() -> None:
    assert (
        personal_data_contour(
            settings(
                llm_provider="gigachat",
                llm_profile="gigachat-2-pro",
                embed_provider="gigachat",
                embed_profile="gigachat-embeddings",
            )
        )
        is True
    )


def test_local_stages_do_not_leave_the_contour() -> None:
    """Hashing and the extractive answerer compute on this machine and call nothing."""
    assert (
        personal_data_contour(
            settings(llm_provider="extractive", embed_provider="hashing", embed_profile="")
        )
        is True
    )


def test_one_cross_border_stage_is_enough_to_leave_the_contour() -> None:
    """The question is not "is the answer model local" but "does anything leave"."""
    assert (
        personal_data_contour(
            settings(
                llm_provider="gigachat",
                llm_profile="gigachat-2-pro",
                embed_provider="gigachat",
                embed_profile="gigachat-embeddings",
                rerank_base_url="https://openrouter.ai/api/v1",
                rerank_profile="openrouter-cohere-rerank-v3.5",
            )
        )
        is False
    )
