#!/usr/bin/env bash
# End-to-end proof for a reviewer: compose up, seed the demo, then ask the admin API whether the
# numbers the docs promise are really there. Exits non-zero on the first promise that is not.
set -Eeuo pipefail

cd "$(dirname "$0")/.."

BASE="${BASE_URL:-http://localhost:8000}"
CABINET="${CABINET_URL:-http://localhost:3000}"
TOKEN="${ADMIN_TOKEN:-dev-hr-token}"
EXPECT_RUNS="${EXPECT_RUNS:-3}"
EXPECT_HIGH_RISK="${EXPECT_HIGH_RISK:-2}"
EXPECT_QUESTIONS="${EXPECT_QUESTIONS:-2}"
EXPECT_DOCUMENTS="${EXPECT_DOCUMENTS:-69}"
export EXPECT_RUNS EXPECT_HIGH_RISK EXPECT_QUESTIONS EXPECT_DOCUMENTS

say() { printf '%-24s %s\n' "$1" "$2"; }
wait_for() {
    for _ in $(seq 1 90); do
        curl -fsS -m 2 "$1" >/dev/null 2>&1 && return 0
        sleep 1
    done
    return 1
}

docker compose up -d --build >/dev/null
wait_for "$BASE/healthz" || {
    echo "api did not answer $BASE/healthz; last log lines:" >&2
    docker compose logs --tail=40 api >&2
    exit 1
}
wait_for "$CABINET/" || {
    echo "cabinet did not answer $CABINET/; last log lines:" >&2
    docker compose logs --tail=20 admin >&2
    exit 1
}
say "stack" "up (postgres, migrate, api, worker, admin)"

make --no-print-directory demo-data >/dev/null

jar="$(mktemp)"
trap 'rm -f "$jar"' EXIT
code="$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$BASE/admin/api/v1/session" \
    -H 'Content-Type: application/json' -d "{\"token\":\"$TOKEN\"}" -c "$jar")"
if [ "$code" != "204" ]; then
    echo "session answered $code for token '$TOKEN'; set ADMIN_TOKEN to a value from ADMIN_TOKENS" >&2
    exit 1
fi

overview="$(curl -fsS -b "$jar" "$BASE/admin/api/v1/analytics/overview")"
knowledge="$(curl -fsS -b "$jar" "$BASE/admin/api/v1/knowledge")"
questions="$(curl -fsS -b "$jar" "$BASE/admin/api/v1/questions")"

python3 - "$overview" "$knowledge" "$questions" <<'PY'
import json
import os
import sys

overview, knowledge, questions = (json.loads(arg) for arg in sys.argv[1:4])
expected = {
    "runs_in_progress": (overview.get("active_runs"), int(os.environ["EXPECT_RUNS"])),
    "high_risk": (overview.get("high_risk"), int(os.environ["EXPECT_HIGH_RISK"])),
    "questions_without_answer": (overview.get("unanswered_questions"), int(os.environ["EXPECT_QUESTIONS"])),
    "documents_in_the_corpus": (len(knowledge.get("items", [])), int(os.environ["EXPECT_DOCUMENTS"])),
}
wrong = {name: {"got": got, "want": want} for name, (got, want) in expected.items() if got != want}
if wrong:
    print("demo numbers differ from docs/product/demo-script.md:", json.dumps(wrong, ensure_ascii=False), file=sys.stderr)
    raise SystemExit(1)
total = questions.get("total")
if total is not None and total != expected["questions_without_answer"][1]:
    print(f"question list total is {total}, the overview promises {expected['questions_without_answer'][1]}", file=sys.stderr)
    raise SystemExit(1)
print("  " + "  ".join(f"{name}={got}" for name, (got, _) in expected.items()))
PY

say "api" "$BASE/healthz 200"
say "cabinet" "$CABINET (token: $TOKEN)"
echo "verify-demo: ok"
