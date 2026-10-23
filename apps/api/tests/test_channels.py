"""Channel profiles and the two pure renderers: split a body, refuse a keyboard that cannot fly."""

from __future__ import annotations

from pathlib import Path

import pytest

from onboarding.app.channels.profiles import ChannelProfileLibrary
from onboarding.app.scenarios import ScenarioCatalog
from onboarding.core.channels import ChannelProfile, ChannelProfileError, fit_keyboard, fit_text
from onboarding.core.models import MAX_MESSAGE_CHARS, Button, Channel

CHANNEL_PROFILES = Path(__file__).resolve().parents[1] / "channel-profiles"
CONTRACTS = Path(__file__).resolve().parents[3] / "docs" / "contracts"
SCENARIOS = Path(__file__).resolve().parents[1] / "onboarding" / "scenarios"


def profile(**overrides: object) -> ChannelProfile:
    values: dict[str, object] = {"channel": Channel.TELEGRAM, "max_text_chars": 40}
    values.update(overrides)
    return ChannelProfile(**values)  # type: ignore[arg-type]


def test_a_short_body_is_sent_whole() -> None:
    assert fit_text("Сколько дней отпуска?", profile()) == ("Сколько дней отпуска?",)


def test_a_body_at_the_limit_is_not_split() -> None:
    text = "а" * 40
    assert fit_text(text, profile()) == (text,)


def test_a_long_body_splits_at_sentence_boundaries() -> None:
    text = (
        "Первый день начинается с пропуска. "
        "Пропуск выдаёт охрана на первом этаже. "
        "Далее вас встретит наставник."
    )

    parts = fit_text(text, profile())

    assert all(len(part) <= 40 for part in parts)
    assert all(part.endswith(".") for part in parts)
    assert " ".join(parts) == text


def test_splitting_loses_no_word() -> None:
    text = " ".join(f"слово{index}" for index in range(200))

    parts = fit_text(text, profile(max_text_chars=100))

    assert all(len(part) <= 100 for part in parts)
    assert " ".join(parts).split() == text.split()


def test_paragraphs_are_packed_before_they_are_cut() -> None:
    text = "А.\n\n\n\nБ."

    parts = fit_text(text, profile(max_text_chars=5))

    assert parts == ("А. Б.",)


def test_a_word_longer_than_the_channel_is_cut_rather_than_refused() -> None:
    parts = fit_text("б" * 120, profile(max_text_chars=40))

    assert [len(part) for part in parts] == [40, 40, 40]


def test_a_keyboard_within_the_limits_passes_unchanged() -> None:
    keyboard = ((Button(id="checklist_done", text="Готово"),),)

    assert fit_keyboard(keyboard, profile()) == keyboard


def test_too_many_rows_is_refused() -> None:
    keyboard = tuple((Button(id=f"b{index}", text="ok"),) for index in range(4))

    with pytest.raises(ChannelProfileError, match="keyboard rows"):
        fit_keyboard(keyboard, profile(max_keyboard_rows=3))


def test_too_many_buttons_in_a_row_is_refused() -> None:
    keyboard = ((Button(id="a", text="a"), Button(id="b", text="b")),)

    with pytest.raises(ChannelProfileError, match="buttons in a row"):
        fit_keyboard(keyboard, profile(max_buttons_per_row=1))


def test_a_callback_payload_above_the_channel_limit_is_refused() -> None:
    keyboard = ((Button(id="x" * 65, text="ok"),),)

    with pytest.raises(ChannelProfileError, match="bytes"):
        fit_keyboard(keyboard, profile(callback_payload_bytes=64))


def test_a_profile_may_lower_the_domain_cap_but_not_raise_it() -> None:
    profile(max_text_chars=MAX_MESSAGE_CHARS).validate()

    with pytest.raises(ChannelProfileError, match="domain cap"):
        profile(max_text_chars=MAX_MESSAGE_CHARS + 1).validate()


def test_the_shipped_profiles_satisfy_the_contract() -> None:
    library = ChannelProfileLibrary(CHANNEL_PROFILES, CONTRACTS / "channel-profile.schema.json")

    loaded = library.load_all()

    assert set(loaded) == set(Channel)
    for channel, shipped in loaded.items():
        assert shipped.channel is channel
        assert shipped.max_text_chars <= MAX_MESSAGE_CHARS


def test_a_profile_for_the_wrong_channel_is_refused(tmp_path: Path) -> None:
    schema = CONTRACTS / "channel-profile.schema.json"
    (tmp_path / "vk.yaml").write_text(
        "channel: telegram\nmax_text_chars: 1000\nmarkup: none\nmessages_per_second: 1\n",
        encoding="utf-8",
    )
    library = ChannelProfileLibrary(tmp_path, schema)

    with pytest.raises(ChannelProfileError, match="channel is 'telegram'"):
        library.load(Channel.VK)


def test_a_missing_profile_is_named_in_the_error(tmp_path: Path) -> None:
    library = ChannelProfileLibrary(tmp_path, CONTRACTS / "channel-profile.schema.json")

    with pytest.raises(ChannelProfileError, match="missing channel profile"):
        library.load(Channel.MAX)


def test_the_shipped_scenarios_fit_every_channel_keyboard() -> None:
    """A scenario that cannot be rendered on an enabled channel is a startup error (ADR 0019)."""
    library = ChannelProfileLibrary(CHANNEL_PROFILES, CONTRACTS / "channel-profile.schema.json")
    catalog = ScenarioCatalog.load(SCENARIOS)

    for shipped in library.load_all().values():
        for scenario_id in catalog.ids():
            for step in catalog.active(scenario_id).steps.values():
                fit_keyboard(step.keyboard, shipped)
