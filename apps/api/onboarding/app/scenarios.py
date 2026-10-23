"""Scenario catalog: YAML files validated at startup.

The catalog fails to load on an invalid file, so a broken scenario is a deployment error rather
than a surprise on someone's first day. The highest version of each id is the active one.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from onboarding.core.models import Scenario, ScenarioError
from onboarding.core.scenario import parse_scenario


class ScenarioCatalogError(ValueError):
    """The scenario directory is unusable as a whole."""


class ScenarioCatalog:
    def __init__(self, scenarios: dict[tuple[str, int], Scenario]) -> None:
        if not scenarios:
            raise ScenarioCatalogError("no scenarios loaded")
        self._scenarios = dict(scenarios)

    @classmethod
    def load(cls, directory: Path) -> ScenarioCatalog:
        scenarios: dict[tuple[str, int], Scenario] = {}
        paths = sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml"))
        if not paths:
            raise ScenarioCatalogError(f"{directory}: no scenario files")
        for path in paths:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ScenarioCatalogError(f"{path}: expected a mapping")
            try:
                scenario = parse_scenario(raw)
            except ScenarioError as error:
                raise ScenarioCatalogError(f"{path}: {error}") from None
            key = (scenario.id, scenario.version)
            if key in scenarios:
                raise ScenarioCatalogError(f"duplicate scenario {scenario.id} v{scenario.version}")
            scenarios[key] = scenario
        return cls(scenarios)

    def get(self, scenario_id: str, version: int) -> Scenario:
        try:
            return self._scenarios[(scenario_id, version)]
        except KeyError:
            raise ScenarioCatalogError(
                f"scenario {scenario_id!r} v{version} is not deployed"
            ) from None

    def active(self, scenario_id: str) -> Scenario:
        versions = [version for (sid, version) in self._scenarios if sid == scenario_id]
        if not versions:
            raise ScenarioCatalogError(f"no versions of scenario {scenario_id!r}")
        return self._scenarios[(scenario_id, max(versions))]

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted({scenario_id for scenario_id, _ in self._scenarios}))
