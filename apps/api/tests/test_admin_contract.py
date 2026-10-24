"""The cockpit and the API agree on the paths, or the client is broken at runtime.

The TypeScript client calls URLs the API promises in its OpenAPI document; nothing else connects
the two. A rename on either side compiles on both and fails in the browser, so the paths are read
from the source and compared with the schema. The allowlist below is the honest part: the API may
serve endpoints the cabinet has not adopted, and adding one has to be a deliberate edit here.
"""

from __future__ import annotations

import re
from pathlib import Path

from onboarding.api.app import create_app
from onboarding.app.settings import Settings

ROOT = Path(__file__).resolve().parents[3]
CLIENT = ROOT / "apps" / "admin" / "src"
PREFIX = "/admin/api/v1"

# Endpoints that exist for operators and scripts, not for the cabinet yet.
API_ONLY = {
    f"{PREFIX}/employees",
    f"{PREFIX}/employees/bulk",
    f"{PREFIX}/identities",
}

_CALL = re.compile(r"/admin/api/v1[^`\"'\n]*")
_PARAM = re.compile(r"\$\{[^}]*\}|\{[^}]*\}")


def normalise(path: str) -> str:
    """One placeholder for every parameter, no query string: the shape, not an example."""
    return _PARAM.sub("{}", path.split("?", 1)[0].rstrip("/"))


def client_paths() -> set[str]:
    paths: set[str] = set()
    for source in sorted(CLIENT.rglob("*.ts*")):
        if ".test." in source.name:
            # A test may use a concrete id; only the client itself describes the contract.
            continue
        for match in _CALL.finditer(source.read_text(encoding="utf-8")):
            paths.add(normalise(match.group(0)))
    return paths


def server_paths() -> set[str]:
    schema = create_app(
        Settings(_env_file=None, admin_tokens_raw="token:hr_admin:hr-1")
    ).openapi()
    return {normalise(path) for path in schema["paths"]}


def test_every_path_the_cabinet_calls_exists_in_the_api() -> None:
    missing = client_paths() - server_paths()

    assert not missing, f"the cabinet calls paths the API does not serve: {sorted(missing)}"


def test_an_api_endpoint_that_disappears_is_a_deliberate_contract_change() -> None:
    unused = server_paths() - client_paths()

    assert unused == API_ONLY, (
        "the set of endpoints the cabinet does not call changed: "
        f"{sorted(unused)}; update the client or the allowlist"
    )


def test_the_comparison_is_not_vacuous() -> None:
    assert len(client_paths()) >= 12
    assert len(server_paths()) >= 15
