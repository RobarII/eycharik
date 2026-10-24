"""The operator CLI, tested where it decides something.

Most of the file is argument plumbing and a container call, which no test makes truer. What is
worth pinning: a dispatch that reaches the right command, a guardrail that refuses before the
database, a dry-run extraction that separates "accepted" from "cannot read this", and a seed file
that is validated before a connection is opened.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import ClassVar

import pytest

from onboarding.app.settings import Settings
from onboarding.cli import _employee_row, _extract, _seed, _subscribe, _webhook, main
from onboarding.core.models import Channel

from .files import blank_pdf, digital_pdf


def settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]


def test_check_is_the_default_command_and_reports_what_it_built(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class Catalog:
        def ids(self) -> list[str]:
            return ["onboarding_default"]

    class Extractor:
        class profile:  # noqa: N801 - the CLI prints these two attributes
            name = "native"
            family = "none"

    class FakeContainer:
        catalog = Catalog()
        extractor = Extractor()

        async def aclose(self) -> None:
            pass

    def fake_build(settings: object) -> FakeContainer:
        del settings
        return FakeContainer()

    monkeypatch.setattr("onboarding.cli.build_container", fake_build)
    def fake_settings() -> Settings:
        return settings()

    monkeypatch.setattr("onboarding.cli.Settings", fake_settings)

    assert main(["check"]) == 0

    printed = capsys.readouterr().out
    assert "scenarios: onboarding_default" in printed
    assert "extraction: native (family none)" in printed


async def test_a_digital_file_is_accepted_by_the_dry_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "policy.pdf"
    path.write_bytes(digital_pdf(["Ежегодный оплачиваемый отпуск — 28 календарных дней."]))

    code = await _extract(settings(), argparse.Namespace(file=path, profile="native"))

    assert code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["route"] == "native_text"
    assert summary["accepted"] is True
    assert summary["characters"] > 0


async def test_a_scan_is_refused_with_the_reason_of_the_profile(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "scan.pdf"
    path.write_bytes(blank_pdf())

    code = await _extract(settings(), argparse.Namespace(file=path, profile="native"))

    assert code == 2
    assert "cannot read this file" in capsys.readouterr().out


async def test_vk_registration_prints_the_operator_steps_without_a_client() -> None:
    args = argparse.Namespace(channel="vk", url="https://host/webhook/vk")
    resolved = settings(channels_raw="vk", vk_confirmation_code="code", vk_webhook_secret="secret")

    assert await _webhook(resolved, args) == 0


async def test_a_disabled_channel_is_named_before_any_network_call() -> None:
    args = argparse.Namespace(channel="telegram", url="https://host/webhook/telegram")

    with pytest.raises(SystemExit, match="telegram is not enabled"):
        await _webhook(settings(channels_raw="max"), args)


async def test_subscribe_refuses_a_deployment_without_the_max_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeContainer:
        senders: ClassVar[dict[Channel, object]] = {}

        async def aclose(self) -> None:
            pass

    def fake_build(settings: object) -> FakeContainer:
        del settings
        return FakeContainer()

    monkeypatch.setattr("onboarding.cli.build_container", fake_build)
    args = argparse.Namespace(url="https://host/webhook/max", types="message_created")

    with pytest.raises(SystemExit, match="the MAX channel is not configured"):
        await _subscribe(settings(), args)


def test_a_seed_file_is_validated_before_the_database_is_opened(tmp_path: Path) -> None:
    path = tmp_path / "employees.json"
    path.write_text(json.dumps({"employees": []}), encoding="utf-8")

    with pytest.raises(SystemExit, match="expected a list of employees"):
        asyncio.run(_seed(settings(), path))


def test_an_employee_row_is_a_typed_value_not_a_mapping() -> None:
    row = _employee_row(
        {
            "id": 1001,
            "name": "Анна Смирнова",
            "role": "Инженер",
            "department": "ИТ",
            "recruiter_id": "rec-1",
            "started_at": "2026-10-20",
            "audience": ["all", "dept:it"],
        }
    )

    assert row["id"] == "1001"
    assert row["started_at"].isoformat() == "2026-10-20"  # type: ignore[union-attr]
    assert row["scenario_id"] == "onboarding_default"

    with pytest.raises(SystemExit, match="each employee must be an object"):
        _employee_row("1001")
