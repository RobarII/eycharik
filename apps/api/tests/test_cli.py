from __future__ import annotations

import pytest

from onboarding.app.settings import Settings
from onboarding.cli import _demo


async def test_demo_refuses_a_non_local_environment() -> None:
    settings = Settings(_env_file=None, environment="staging")

    with pytest.raises(SystemExit, match="ENVIRONMENT=local"):
        await _demo(settings, reset=False, assume_yes=False)


async def test_destructive_reset_needs_confirmation() -> None:
    settings = Settings(_env_file=None, environment="local")

    with pytest.raises(SystemExit, match="--yes"):
        await _demo(settings, reset=True, assume_yes=False)
