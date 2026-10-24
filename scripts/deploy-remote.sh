#!/usr/bin/env bash
# Deploy one immutable commit on the server. Run as the unprivileged deploy user from the repo
# checkout; the host nginx config is managed by scripts/bootstrap-vps.sh, not by this script.
#
# The order matters, and the one rule is: a migration that fails is never "rolled back" by putting
# old images on top of a new schema. Before the first migration we take a dump, and if the migration
# itself fails we stop and point at that dump instead of pretending the rollback worked.
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="${DEPLOY_ROOT:-/opt/onboarding}"
COMPOSE_FILE="docker-compose.yml"
PROD_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/onboarding}"
SMOKE_PASSES="${SMOKE_PASSES:-3}"

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
export TAG="sha-$SHA"

# Set once the database schema may already be newer than `PREV`; the rollback refuses while it is 1.
SCHEMA_TOUCHED=0
DUMP=""

log() { printf 'deploy: %s\n' "$*"; }

notify() {
    [ -n "${DEPLOY_NOTIFY_URL:-}" ] || return 0
    curl -fsS -m 5 -X POST -H 'Content-Type: application/json' \
        -d "$(printf '{"text":"deploy %s: %s"}' "$SHA" "$1")" \
        "$DEPLOY_NOTIFY_URL" >/dev/null 2>&1 || true
}

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
    if [ "$SCHEMA_TOUCHED" = "1" ]; then
        cat >&2 <<EOF
deploy: not rolling the images back. The schema already saw a migration, and old code on a new
deploy: schema fails in ways a rollback hides. The database is still on the new schema:
deploy:   dump taken before the migration: ${DUMP:-none}
deploy:   repair forward with a fix commit, or restore the dump on purpose:
deploy:     CONFIRM_RESTORE=yes ./scripts/restore.sh ${DUMP:-<dump>}
EOF
        return 0
    fi
    if [ -z "$PREV" ] || [ "$PREV" = "$SHA" ]; then
        echo "deploy: no previous release to roll back to" >&2
        return 0
    fi
    echo "deploy: rolling back to $PREV" >&2
    # Keep the current compose files: a rollback changes the image tag, not the infrastructure
    # definition. An older commit may not understand the current .env.prod.
    TAG="sha-$PREV" "${COMPOSE[@]}" up -d --no-deps --remove-orphans worker api admin || true
    ./scripts/smoke.sh "$PUBLIC_URL" || true
}

on_error() {
    local code=$?
    trap - ERR
    echo "deploy: failed with exit $code" >&2
    rollback
    notify "failed with exit $code"
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

# The dump is taken while the old api and worker are still writing, so it is not a quiescent
# snapshot. It exists to answer one question: what did the database look like one migration ago.
# A real backup is scripts/backup.sh and its timer; this one only serves the failure path.
install -d -m 700 "$BACKUP_DIR"
DUMP="$BACKUP_DIR/pre-deploy-$(date -u +%Y%m%dT%H%M%SZ)-$SHA.dump"
log "dumping the database before migrating to $DUMP"
./scripts/backup.sh --file "$DUMP"

log "applying migrations"
SCHEMA_TOUCHED=1
"${COMPOSE[@]}" run --rm migrate

log "starting worker and api"
"${COMPOSE[@]}" up -d --no-deps --remove-orphans worker api

wait_healthy api 60 || { echo "deploy: api did not become healthy" >&2; exit 1; }

# The cabinet resolves the API name at startup on older nginx images; start it only after the API
# address is stable. The nginx config also resolves per request, so an API-only restart is safe.
log "starting admin"
"${COMPOSE[@]}" up -d --no-deps --remove-orphans admin

wait_healthy admin 30 || { echo "deploy: admin did not become healthy" >&2; exit 1; }

log "smoke testing $PUBLIC_URL ($SMOKE_PASSES passes)"
for ((pass = 1; pass <= SMOKE_PASSES; pass++)); do
    ./scripts/smoke.sh "$PUBLIC_URL"
    [ "$pass" -lt "$SMOKE_PASSES" ] && sleep 10
done

# Keep the compose environment in step with the running tag so an operator's `docker compose`
# command does not silently target the previous release.
if grep -q '^TAG=' "$ENV_FILE"; then
    sed -i "s/^TAG=.*/TAG=sha-$SHA/" "$ENV_FILE"
else
    printf 'TAG=sha-%s\n' "$SHA" >>"$ENV_FILE"
fi

printf '%s\n' "$SHA" > .deployed_sha.tmp
mv .deployed_sha.tmp .deployed_sha
log "deployed $SHA"
notify "deployed"
"${COMPOSE[@]}" ps
