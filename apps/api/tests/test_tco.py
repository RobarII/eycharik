"""The TCO script is arithmetic the business case quotes, so it gets a test, not a promise.

The numbers here are the ones three documents repeat: 0.0306 ₽ per answer, 11 346.39 ₽ of
infrastructure, 22 730.73 ₽ for two zones. A price edit that moves them without a docs edit fails
here first.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "tco.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed argv, the repo's own script
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )


def test_answer_cost_and_infrastructure_totals() -> None:
    result = run("--newcomers", "50,100", "--answers-per-newcomer", "20", "--hr-hourly-rub", "1000")

    assert result.returncode == 0, result.stderr
    assert "0,0306 ₽/ответ" in result.stdout
    assert "**11 346,39**" in result.stdout
    assert "**22 730,73**" in result.stdout
    assert "138 047,74" in result.stdout
    assert "2 334 937" in result.stdout
    assert "0,0079" in result.stdout


def test_volume_is_a_required_scenario_not_a_default() -> None:
    missing_answers = run("--newcomers", "50")
    missing_newcomers = run("--answers-per-newcomer", "20")

    assert missing_answers.returncode != 0
    assert "--answers-per-newcomer" in missing_answers.stderr
    assert missing_newcomers.returncode != 0
    assert "--newcomers" in missing_newcomers.stderr


def test_setup_cost_is_unknown_until_given() -> None:
    unknown = run("--newcomers", "50", "--answers-per-newcomer", "20")
    known = run("--newcomers", "50", "--answers-per-newcomer", "20", "--setup-rub", "100000")

    assert "внедрение надо получить" in unknown.stdout
    assert "без разовой части" in unknown.stdout
    assert "внедрение 100 000 ₽" in known.stdout
