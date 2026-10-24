#!/usr/bin/env bash
# Preflight for a reviewer: is this machine able to run the demo and the gate at all?
# Read-only. It starts nothing, deletes nothing, and prints what is missing.
set -uo pipefail

cd "$(dirname "$0")/.."

status=0
ok() { printf '  ok   %s\n' "$1"; }
bad() { printf '  FAIL %s\n' "$1"; status=1; }
note() { printf '  note %s\n' "$1"; }

echo "tools"
command -v docker >/dev/null 2>&1 && ok "docker $(docker --version | cut -d' ' -f3 | tr -d ,)" \
    || bad "docker is not installed: install Docker Desktop or OrbStack"
if command -v docker >/dev/null 2>&1; then
    docker info >/dev/null 2>&1 && ok "docker daemon" || bad "docker daemon is not running"
    docker compose version >/dev/null 2>&1 && ok "compose $(docker compose version --short)" \
        || bad "docker compose v2 is missing"
fi
command -v make >/dev/null 2>&1 && ok "make" || bad "make is missing: see demo-data.cmd for Windows"
command -v uv >/dev/null 2>&1 && ok "uv $(uv --version | cut -d' ' -f2)" \
    || bad "uv is missing: make install needs it"
command -v python3 >/dev/null 2>&1 && ok "python3" || bad "python3 is missing"
command -v curl >/dev/null 2>&1 && ok "curl" || bad "curl is missing"

echo "ports"
listening() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }
for port in 3000 8000 55432; do
    if listening "$port"; then
        owner=$(docker ps --format '{{.Names}}' --filter "publish=$port" | head -1)
        if [ -n "$owner" ]; then ok "$port held by $owner (this stack)"
        else bad "$port is taken by a non-compose process: $port is the cabinet, 8000 the api, 55432 postgres"; fi
    else ok "$port free"; fi
done
if listening 5432; then
    note "5432 is busy (a local Postgres or the integration container). Compose uses 55432, so this is fine."
fi

echo "state"
[ -f .env ] && note ".env exists; compose reads it. The demo needs no .env." || ok "no .env (demo defaults apply)"
if [ -n "${ONBOARDING_TEST_DATABASE:-}" ]; then
    ok "ONBOARDING_TEST_DATABASE is set"
else
    note "ONBOARDING_TEST_DATABASE is unset: 'make test' runs offline only, 'make verify' will stop and say so"
fi
docker compose ps >/dev/null 2>&1 && ok "compose project is present" || note "compose project is not created yet"

if [ "$status" -eq 0 ]; then
    echo "doctor: ready. Next: make verify (gate), make demo (walk through it)."
else
    echo "doctor: fix the FAIL lines above, then rerun." >&2
fi
exit "$status"
