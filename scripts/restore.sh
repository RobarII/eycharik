#!/usr/bin/env bash
# Restore a custom-format dump over the live database. Destructive: it stops the API and worker,
# drops the current schema objects, and loads the dump in one transaction.
#
#   CONFIRM_RESTORE=yes scripts/restore.sh /var/backups/onboarding/onboarding-....dump
#
# Migrations are not rolled back. A restore older than the current schema needs a forward migration
# after it; see docs/runbooks/backup.md.
set -Eeuo pipefail
IFS=$'\n\t'

[ "${CONFIRM_RESTORE:-}" = "yes" ] || {
    echo "refusing to restore without CONFIRM_RESTORE=yes" >&2
    exit 2
}
[ "$#" -eq 1 ] || { echo "usage: CONFIRM_RESTORE=yes $0 <dump-file>" >&2; exit 2; }
FILE="$1"
[ -r "$FILE" ] || { echo "cannot read $FILE" >&2; exit 1; }

ROOT="${DEPLOY_ROOT:-/opt/onboarding}"
COMPOSE=(docker compose --project-directory "$ROOT" -f docker-compose.yml -f docker-compose.prod.yml --env-file "$ROOT/.env.prod")
[ -r "$ROOT/.env.prod" ] || { echo "missing $ROOT/.env.prod" >&2; exit 1; }

DB_USER="$("${COMPOSE[@]}" exec -T postgres printenv POSTGRES_USER)"
DB_NAME="$("${COMPOSE[@]}" exec -T postgres printenv POSTGRES_DB)"
[ -n "$DB_USER" ] && [ -n "$DB_NAME" ] || { echo "cannot read POSTGRES_USER/POSTGRES_DB" >&2; exit 1; }

"${COMPOSE[@]}" exec -T postgres pg_restore --list <"$FILE" >/dev/null

echo "restore: stopping api and worker"
"${COMPOSE[@]}" stop worker api
echo "restore: loading $FILE into $DB_NAME"
"${COMPOSE[@]}" exec -T postgres pg_restore \
    --clean --if-exists --no-owner --no-privileges --single-transaction \
    -U "$DB_USER" -d "$DB_NAME" <"$FILE"
echo "restore: starting api and worker"
"${COMPOSE[@]}" start api worker
echo "restore: done; run scripts/smoke.sh and verify the audit log"
