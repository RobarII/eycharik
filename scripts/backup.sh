#!/usr/bin/env bash
# Consistent Postgres backup: custom-format dump, list-verified, optional S3 upload, local retention.
# Run as the deploy user; the systemd unit supplies BACKUP_* from /etc/onboarding-backup.env.
#
#   scripts/backup.sh                          # the nightly backup, kept for BACKUP_KEEP_DAYS
#   scripts/backup.sh --file /path/to.dump     # one dump where the caller wants it, no pruning
#
# `--file` is what scripts/deploy-remote.sh calls before a migration: the deploy needs to know the
# dump exists, so a concurrent backup is a failure there, not a silently skipped success.
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="${DEPLOY_ROOT:-/opt/onboarding}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/onboarding}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
COMPOSE=(docker compose --project-directory "$ROOT" -f docker-compose.yml -f docker-compose.prod.yml --env-file "$ROOT/.env.prod")

EXPLICIT_FILE=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --file)
            [ "$#" -ge 2 ] || { echo "--file needs a path" >&2; exit 2; }
            EXPLICIT_FILE="$2"
            shift 2
            ;;
        -h|--help)
            sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

[ -r "$ROOT/.env.prod" ] || { echo "missing $ROOT/.env.prod" >&2; exit 1; }
install -d -m 700 "$BACKUP_DIR"
exec 9>"$BACKUP_DIR/.lock"
if ! flock -n 9; then
    if [ -n "$EXPLICIT_FILE" ]; then
        echo "another backup holds the lock: refusing to report a dump that was never taken" >&2
        exit 1
    fi
    echo "backup already running" >&2
    exit 0
fi
umask 077

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
if [ -n "$EXPLICIT_FILE" ]; then
    install -d -m 700 "$(dirname "$EXPLICIT_FILE")"
    NAME="$EXPLICIT_FILE"
    TMP="$(mktemp "$(dirname "$EXPLICIT_FILE")/.partial-XXXXXX")"
else
    NAME="$BACKUP_DIR/onboarding-$STAMP.dump"
    TMP="$(mktemp "$BACKUP_DIR/.onboarding-$STAMP.XXXXXX")"
fi
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
mv "$TMP" "$NAME"
trap - EXIT
SIZE="$(du -h "$NAME" | cut -f1)"
echo "backup: wrote $NAME ($SIZE)"

if [ -n "$EXPLICIT_FILE" ]; then
    echo "backup: keeping $NAME (an explicit dump is never pruned or uploaded)"
    exit 0
fi

if [ -n "${BACKUP_S3_URI:-}" ]; then
    command -v aws >/dev/null || { echo "BACKUP_S3_URI is set but aws is not installed" >&2; exit 1; }
    echo "backup: uploading to $BACKUP_S3_URI"
    aws s3 cp "$BACKUP_DIR/$NAME" "${BACKUP_S3_URI%/}/$NAME" --only-show-errors
fi

find "$BACKUP_DIR" -type f -name 'onboarding-*.dump' -mtime "+$KEEP_DAYS" -delete
echo "backup: pruned local dumps older than $KEEP_DAYS days"
