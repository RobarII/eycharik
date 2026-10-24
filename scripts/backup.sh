#!/usr/bin/env bash
# Consistent Postgres backup: custom-format dump, list-verified, optional S3 upload, local retention.
# Run as the deploy user; the systemd unit supplies BACKUP_* from /etc/onboarding-backup.env.
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="${DEPLOY_ROOT:-/opt/onboarding}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/onboarding}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
COMPOSE=(docker compose --project-directory "$ROOT" -f docker-compose.yml -f docker-compose.prod.yml --env-file "$ROOT/.env.prod")

[ -r "$ROOT/.env.prod" ] || { echo "missing $ROOT/.env.prod" >&2; exit 1; }
install -d -m 700 "$BACKUP_DIR"
exec 9>"$BACKUP_DIR/.lock"
flock -n 9 || { echo "backup already running" >&2; exit 0; }
umask 077

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
NAME="onboarding-$STAMP.dump"
TMP="$(mktemp "$BACKUP_DIR/.onboarding-$STAMP.XXXXXX")"
trap 'rm -f "$TMP"' EXIT

DB_USER="$("${COMPOSE[@]}" exec -T postgres printenv POSTGRES_USER)"
DB_NAME="$("${COMPOSE[@]}" exec -T postgres printenv POSTGRES_DB)"
[ -n "$DB_USER" ] && [ -n "$DB_NAME" ] || { echo "cannot read POSTGRES_USER/POSTGRES_DB" >&2; exit 1; }

echo "backup: dumping $DB_NAME"
"${COMPOSE[@]}" exec -T postgres pg_dump \
    --format=custom --no-owner --no-privileges \
    -U "$DB_USER" -d "$DB_NAME" >"$TMP"

# A dump that pg_restore cannot list is not a backup.
"${COMPOSE[@]}" exec -T postgres pg_restore --list <"$TMP" >/dev/null

chmod 600 "$TMP"
mv "$TMP" "$BACKUP_DIR/$NAME"
trap - EXIT
SIZE="$(du -h "$BACKUP_DIR/$NAME" | cut -f1)"
echo "backup: wrote $BACKUP_DIR/$NAME ($SIZE)"

if [ -n "${BACKUP_S3_URI:-}" ]; then
    command -v aws >/dev/null || { echo "BACKUP_S3_URI is set but aws is not installed" >&2; exit 1; }
    echo "backup: uploading to $BACKUP_S3_URI"
    aws s3 cp "$BACKUP_DIR/$NAME" "${BACKUP_S3_URI%/}/$NAME" --only-show-errors
fi

find "$BACKUP_DIR" -type f -name 'onboarding-*.dump' -mtime "+$KEEP_DAYS" -delete
echo "backup: pruned local dumps older than $KEEP_DAYS days"
