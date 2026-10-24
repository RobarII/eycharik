#!/usr/bin/env bash
# Deploy one immutable commit on the server. Run as the unprivileged deploy user from the repo
# checkout; the host nginx config is managed by scripts/bootstrap-vps.sh, not by this script.
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="${DEPLOY_ROOT:-/opt/onboarding}"
COMPOSE_FILE="docker-compose.yml"
PROD_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"

usage() {
    printf 'usage: %s <40-character-commit-sha>\n' "${0##*/}" >&2
    exit 2
}

[ "$#" -eq 1 ] || usage
SHA="$1"
[[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || usage

cd "$ROOT"
[ -f "$COMPOSE_FILE" ] || { echo "missing $ROOT/$COMPOSE_FILE" >&2; exit 1; }
[ -f "$PROD_FILE" ] || { echo "missing $ROOT/$PROD_FILE" >&2; exit 1; }
[ -r "$ENV_FILE" ] || { echo "missing $ROOT/$ENV_FILE" >&2; exit 1; }

umask 022
exec 9>"$ROOT/.deploy.lock"
flock -n 9 || { echo "another deploy is running" >&2; exit 1; }

PREV="$(cat .deployed_sha 2>/dev/null || true)"
[[ -z "$PREV" || "$PREV" =~ ^[0-9a-f]{40}$ ]] || PREV=""

PUBLIC_URL="$(sed -n 's/^PUBLIC_URL=//p' "$ENV_FILE" | tail -n 1)"
PUBLIC_URL="${PUBLIC_URL:-https://bot.state3407.space}"

COMPOSE=(docker compose --project-directory "$ROOT" -f "$COMPOSE_FILE" -f "$PROD_FILE" --env-file "$ENV_FILE")
export TAG="$SHA"

log() { printf 'deploy: %s\n' "$*"; }

wait_healthy() {
    local service="$1" tries="${2:-30}" cid status i
    for ((i = 0; i < tries; i++)); do
        cid="$("${COMPOSE[@]}" ps -q "$service" 2>/dev/null || true)"
        if [ -n "$cid" ]; then
            status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null || true)"
            [ "$status" = "healthy" ] && return 0
            [ "$status" = "exited" ] && return 1
        fi
        sleep 2
    done
    return 1
}

rollback() {
    trap - ERR
    if [ -z "$PREV" ] || [ "$PREV" = "$SHA" ]; then
        echo "deploy: no previous release to roll back to" >&2
        return 0
    fi
    echo "deploy: rolling back to $PREV" >&2
    # Keep the current compose files: a rollback changes the image tag, not the infrastructure
    # definition. An older commit may not understand the current .env.prod.
    TAG="$PREV" "${COMPOSE[@]}" up -d --no-deps --remove-orphans worker api admin || true
    ./scripts/smoke.sh "$PUBLIC_URL" || true
}

on_error() {
    local code=$?
    trap - ERR
    echo "deploy: failed with exit $code" >&2
    rollback
    exit "$code"
}
trap on_error ERR

log "fetching $SHA"
git fetch --prune --tags origin
git checkout --force "$SHA"

log "pulling images"
"${COMPOSE[@]}" pull api worker migrate admin

log "starting postgres"
"${COMPOSE[@]}" up -d postgres
wait_healthy postgres 60 || { echo "deploy: postgres did not become healthy" >&2; exit 1; }

log "applying migrations"
"${COMPOSE[@]}" run --rm migrate

log "starting worker, then api and admin"
"${COMPOSE[@]}" up -d --no-deps --remove-orphans worker
"${COMPOSE[@]}" up -d --no-deps --remove-orphans api admin

wait_healthy api 60 || { echo "deploy: api did not become healthy" >&2; exit 1; }
wait_healthy admin 30 || { echo "deploy: admin did not become healthy" >&2; exit 1; }

log "smoke testing $PUBLIC_URL"
./scripts/smoke.sh "$PUBLIC_URL"

# Keep the compose environment in step with the running tag so an operator's `docker compose`
# command does not silently target the previous release.
if grep -q '^TAG=' "$ENV_FILE"; then
    sed -i "s/^TAG=.*/TAG=$SHA/" "$ENV_FILE"
else
    printf 'TAG=%s\n' "$SHA" >>"$ENV_FILE"
fi

printf '%s\n' "$SHA" > .deployed_sha.tmp
mv .deployed_sha.tmp .deployed_sha
log "deployed $SHA"
"${COMPOSE[@]}" ps
