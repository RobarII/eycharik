# Runbook: backup and restore

The single Postgres holds runs, jobs, the outbox, knowledge chunks, audit rows, and vectors. Losing
it loses the product state, so the backup is a dump of that database, not a copy of the Docker
volume.

## What runs

`scripts/backup.sh`:

1. Takes a lock so two runs cannot overlap.
2. Runs `pg_dump --format=custom --no-owner --no-privileges` inside the Postgres container.
3. Proves the dump is readable with `pg_restore --list`.
4. Writes `onboarding-<UTC timestamp>.dump` with mode `600`.
5. Uploads it to `BACKUP_S3_URI` when set; a failed upload fails the run.
6. Deletes local dumps older than `BACKUP_KEEP_DAYS`.

The systemd timer `onboarding-backup.timer` runs it daily at 03:30 UTC with a random delay. The
service runs as `deploy`; `NoNewPrivileges` and `PrivateTmp` are on.

Configuration lives in `/etc/onboarding-backup.env`, not in the repository:

```bash
BACKUP_DIR=/var/backups/onboarding
BACKUP_KEEP_DAYS=14
BACKUP_S3_URI=s3://bucket/onboarding
# AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY or an instance role
```

`BACKUP_DIR` must be writable by `deploy`. `BACKUP_S3_URI` needs the `aws` CLI and credentials
that can write only that prefix. Use server-side encryption and a lifecycle rule on the bucket; the
dump contains personal data and must not be public.

## Check it

```bash
systemctl status onboarding-backup.timer
systemctl start onboarding-backup.service
journalctl -u onboarding-backup.service -n 50 --no-pager
ls -lh /var/backups/onboarding
```

The service succeeds only when the dump lists and, if configured, uploads.

## Restore drill

Run a drill on a staging host before the first real employee, and after a schema change that
touches a large table. A restore is destructive: it stops the API and worker, drops the current
schema objects, and loads the dump in one transaction.

```bash
cd /opt/onboarding
CONFIRM_RESTORE=yes scripts/restore.sh /var/backups/onboarding/onboarding-20261024T033000Z.dump
BASE_URL=https://bot.example.com scripts/smoke.sh
```

Then verify the audit log and one known employee:

```sql
select count(*) from employees;
select name, created_at from audit_log order by created_at desc limit 20;
```

The restore does not roll migrations back. A dump older than the current schema needs
`alembic upgrade head` after the restore; a dump newer than the image needs the matching image tag.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `pg_dump` exits non-zero | Postgres down or disk full | start Postgres, free space, rerun |
| upload fails | missing `aws`, expired credentials, wrong prefix | fix credentials; the run stays failed until it succeeds |
| timer inactive | unit not enabled | `systemctl enable --now onboarding-backup.timer` |
| restore fails mid-way | dump corrupt or schema mismatch | keep the API stopped, inspect `pg_restore` output, retry with the matching image |
| disk fills with dumps | `BACKUP_KEEP_DAYS` too large | lower it, move retention to the bucket lifecycle |

A backup that has never been restored is a hypothesis. Keep the drill result in
`docs/measurements/` if it changes an operational number.
