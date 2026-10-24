"""The composition root is code, so it is covered like code.

A messenger without credentials must not be constructed: a half-configured channel has to answer
404, not fail a delivery at send time (ADR 0019). The classifier has one more rule — a prompt
provider without a key is a deployment that answers with the keyword fallback, not one that crashes
on the first survey.
"""

from __future__ import annotations

import pytest

from onboarding.app import container as composition
from onboarding.app.channels.max.client import MaxClient
from onboarding.app.channels.telegram.client import TelegramClient
from onboarding.app.channels.vk.client import VkClient
from onboarding.app.container import Container, build_container
from onboarding.app.settings import Settings
from onboarding.core.models import Channel

DATABASE = "postgresql+asyncpg://onboarding:onboarding@localhost:5432/onboarding"


def settings(**overrides: object) -> Settings:
    # A profile is a deliberate choice; an extractive answerer needs none, and no test here may
    # depend on which model a developer happens to have configured.
    values: dict[str, object] = {"database_url": DATABASE, "llm_provider": "extractive"}
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


def full_credentials(**overrides: object) -> Settings:
    return settings(
        channels_raw="max,telegram,vk",
        max_webhook_secret="max-secret",
        max_bot_token="max-token",
        telegram_webhook_secret="telegram-secret",
        telegram_bot_token="telegram-token",
        vk_webhook_secret="vk-secret",
        vk_confirmation_code="vk-code",
        vk_access_token="vk-token",
        **overrides,
    )


async def test_a_channel_without_credentials_is_not_constructed() -> None:
    container = build_container(settings(channels_raw="max,telegram,vk"))
    try:
        assert container.senders == {}
    finally:
        await container.aclose()


async def test_every_configured_channel_gets_its_own_sender() -> None:
    container = build_container(full_credentials())
    try:
        assert isinstance(container.senders[Channel.MAX], MaxClient)
        assert isinstance(container.senders[Channel.TELEGRAM], TelegramClient)
        assert isinstance(container.senders[Channel.VK], VkClient)
        assert set(container.senders) == {Channel.MAX, Channel.TELEGRAM, Channel.VK}
    finally:
        await container.aclose()


async def test_the_worker_graph_is_wired_end_to_end() -> None:
    container = build_container(full_credentials())
    try:
        assert isinstance(container, Container)
        assert container.queue is not None
        assert container.dispatcher is not None
        assert container.scheduler is not None
        assert container.extractor is not None
        assert container.indexer is not None
        # The shipped profile reads digital documents and refuses a scan; it never guesses.
        assert container.extractor.profile.name == "native"
        assert container.extractor.profile.family == "none"
    finally:
        await container.aclose()


async def test_closing_the_container_closes_its_http_client() -> None:
    container = build_container(full_credentials())
    http = container.http

    await container.aclose()

    assert http.is_closed


def test_a_prompt_classifier_without_a_model_is_off_not_broken() -> None:
    """The survey still records the answer; the risk radar only loses its model signal."""

    class Unused:
        def __getattr__(self, name: str) -> object:
            raise AssertionError(f"a disabled classifier must not touch {name}")

    classifier = composition._classifier(
        settings(llm_provider="openai", sentiment_provider="prompt"),
        clock=Unused(),  # type: ignore[arg-type]
        http=Unused(),  # type: ignore[arg-type]
        llm=Unused(),  # type: ignore[arg-type]
        prompts=Unused(),  # type: ignore[arg-type]
        audit=Unused(),  # type: ignore[arg-type]
    )

    assert classifier is None


async def test_a_misconfigured_classifier_is_a_startup_error_named_for_the_operator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise ValueError("JEV_API_KEY is not set")

    monkeypatch.setattr(composition, "build_sentiment", refuse)

    with pytest.raises(RuntimeError, match="sentiment provider misconfigured: JEV_API_KEY"):
        build_container(settings(sentiment_provider="jev", jev_api_key="jev-key"))
