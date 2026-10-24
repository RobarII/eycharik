#!/usr/bin/env bash
# Public smoke test for a deployed stack. It proves the TLS proxy reaches the API, the cabinet
# answers with its security headers, and the webhook rejects an unsigned request.
set -Eeuo pipefail

BASE_URL="${BASE_URL:-${1:-https://bot.state3407.space}}"
BASE_URL="${BASE_URL%/}"
CURL=(curl -fsS --max-time 15)

fail() {
    printf 'smoke: %s\n' "$*" >&2
    exit 1
}

body="$("${CURL[@]}" "$BASE_URL/healthz")" || fail "healthz is not reachable at $BASE_URL"
grep -q '"status":"ok"' <<<"$body" || fail "healthz did not return status ok: $body"

"${CURL[@]}" -o /dev/null "$BASE_URL/readyz" || fail "readyz is not ready (database?)"

code="$(curl -sS --max-time 15 -o /dev/null -w '%{http_code}' \
    -X POST "$BASE_URL/webhook/max" \
    -H 'Content-Type: application/json' \
    -d '{}')" || fail "webhook request failed"
[ "$code" = "401" ] || fail "unsigned webhook answered $code, expected 401"

headers="$(curl -sSI --max-time 15 "$BASE_URL/")" || fail "cabinet is not reachable at $BASE_URL"
grep -qi '^content-security-policy:' <<<"$headers" || fail "cabinet response has no CSP header"
grep -qi '^x-frame-options: *DENY' <<<"$headers" || fail "cabinet response has no X-Frame-Options: DENY"
grep -qi '^x-content-type-options: *nosniff' <<<"$headers" || fail "cabinet response has no nosniff"

code="$(curl -sS --max-time 15 -o /dev/null -w '%{http_code}' "$BASE_URL/metrics")" || fail "metrics request failed"
case "$code" in
    401|403) ;;
    *) fail "metrics answered $code, expected 401 or 403" ;;
esac

printf 'smoke: ok %s\n' "$BASE_URL"
