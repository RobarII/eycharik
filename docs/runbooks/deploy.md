# Runbook: deploy

The deployment is one VM running the compose stack behind the host nginx. Images are built in CI,
pushed to GHCR, and pulled by immutable commit SHA. The host never builds an image, and nginx is the
only process listening on 443.

Current demo host: `bot.state3407.space` on a 1 vCPU / 921 MB VPS
([capacity](../measurements/2026-10-23-demo-vps-capacity.md)). That is enough for a demo, not
for real employee data: the VPS is outside Russia (152-ФЗ) and the RAM headroom is thin. A pilot
moves to a Russian host with 2–4 GB and keeps the same compose files.

## Preconditions

- `make check` is green. `make eval-retrieval` is green; `make eval` is green if a provider is
  reachable.
- Every schema change has a migration under `apps/api/onboarding/migrations/versions/`.
- The release workflow produced `ghcr.io/<owner>/moshackathon-api:<sha>` and
  `ghcr.io/<owner>/moshackathon-admin:<sha>`.
- `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PORT`, `DEPLOY_PATH` are repository variables;
  `DEPLOY_SSH_KEY` and `DEPLOY_KNOWN_HOSTS` are repository or `production` environment secrets.
- The `production` environment exists. If the plan supports protection rules, add a required
  reviewer; otherwise the human gate is pushing the release tag, and automation must never push
  tags.

## One-time host bootstrap

Generate a dedicated CI key first; the private half goes to the `DEPLOY_SSH_KEY` secret, the public
half to the bootstrap command:

```bash
ssh-keygen -t ed25519 -C github-actions-onboarding -f /tmp/onboarding_deploy -N ''
```

Run as root from a checkout of this repository:

```bash
DOMAIN=bot.example.com \
ACME_EMAIL=ops@example.com \
DEPLOY_PUBKEY="$(cat /tmp/onboarding_deploy.pub)" \
REPO_URL=git@github.com:owner/repo.git \
scripts/bootstrap-vps.sh
```

The script installs missing packages, creates the unprivileged `deploy` user, creates
`/opt/onboarding` and `/var/backups/onboarding`, installs the ACME vhost, issues the certificate,
installs the TLS vhost, and enables the backup timer. It does not edit the other nginx sites, SSH
configuration, or the firewall.

Then, as `deploy`:

```bash
cd /opt/onboarding
docker login ghcr.io -u <github-user>          # read:packages token, stored on the host
cp .env.production.example .env.prod && chmod 600 .env.prod
$EDITOR .env.prod
```

`ENVIRONMENT=production` refuses to start without `MAX_BOT_TOKEN`, `MAX_WEBHOOK_SECRET`,
`LLM_API_KEY`, `ADMIN_TOKENS`, and `METRICS_TOKEN`. The demo model choice also needs
`EMBED_API_KEY` for OpenRouter; GigaChat uses one key for both roles. The API image already installs
the Russian Trusted CA and points `MAX_CA_BUNDLE` at the merged system bundle.

The example env selects OpenCode Go for answers and OpenRouter Qwen3 for embeddings. Both endpoints
answer from the demo host, and neither model runs on it. The GigaChat block is commented out for a
Russian-hosted 152-ФЗ pilot; see [ADR 0025](../decisions/0025-demo-models-on-opencode-and-openrouter.md).

Add the host key to the CI secret once:

```bash
ssh-keyscan -p 22 "$DEPLOY_HOST" 2>/dev/null
```

Put the output in `DEPLOY_KNOWN_HOSTS`. Do not use `StrictHostKeyChecking=no` in CI.

## Release

A push to `main` releases and deploys itself. Nothing has to be tagged by hand:

1. `version` runs `scripts/next_release.py` and picks the next patch after the highest `v*` tag
   (`v0.1.3` -> `v0.1.4`); a commit that already carries a release tag reuses that tag instead of
   inventing a second version.
2. `build` checks out that exact commit and pushes both images under the commit SHA, with
   provenance and an SBOM, plus `org.opencontainers.image.version` set to the version.
3. `tag` creates the annotated `vX.Y.Z` tag on that commit and pushes it, and only runs after both
   images are in the registry: a failed build leaves no tag behind, and a re-run is a no-op.
4. The deploy workflow then calls `scripts/deploy-remote.sh <sha>` over SSH, waiting for the
   `production` environment approval when the plan supports it.

The release workflow needs `contents: write` to push the tag. Tags pushed by `GITHUB_TOKEN` do not
trigger workflows, which is why the deploy follows the release run rather than the tag event: one
push to `main` means one release and one deploy, never a second pass over the tag.

A tag or a manual dispatch still work when the commit must not move `main`:

```bash
git tag v1.2.3
git push origin v1.2.3
gh workflow run release.yml -f ref=<tag-or-sha>
```

Both publish the ref they were given and create no tag. Manual dispatches do not auto-deploy; run
`deploy.yml` with the SHA afterwards.

The remote script, in order:

1. Takes a deploy lock and records the previous SHA.
2. Fetches the commit and checks it out.
3. Pulls the API, worker, migration, and cabinet images.
4. Starts Postgres and waits for its health check.
5. Runs `alembic upgrade head` once, before any new process starts.
6. Starts the worker, then the API and the cabinet.
7. Waits for API and cabinet health, runs `scripts/smoke.sh`, records `.deployed_sha`.
8. On failure, redeploys the previous SHA and runs the smoke test again.

Manual deploy or rollback to an already released SHA:

```bash
gh workflow run deploy.yml -f sha=<40-character-sha>
```

## Smoke test

`scripts/smoke.sh` checks:

- `/healthz` returns `{"status":"ok"}`.
- `/readyz` is `200` (the database answers).
- `POST /webhook/max` without a secret is `401`.
- The cabinet response carries CSP, `X-Frame-Options: DENY`, and `nosniff`.
- `/metrics` is not public (`401` or `403`).

Run it from anywhere:

```bash
BASE_URL=https://bot.example.com scripts/smoke.sh
```

## Register the subscription

After the host and secret are in place:

Run this on the host as `deploy`; the container carries the Russian CA and the production env:

```bash
HOST=bot.example.com
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod \
  run --rm --no-deps api python -m onboarding.cli subscribe \
  --url "https://$HOST/webhook/max" \
  --types message_created,bot_started
```

Re-running replaces the subscription for this bot. Tunnels change hostnames; re-register after
every tunnel restart. Telegram and VK register their webhooks their own way; the same runbook
covers both.

Send `/start` from a test account. Expect: an `events` row, a `jobs` row that reaches `done`, an
outbox row that reaches `sent`, and one welcome message in MAX.

## Verification queries

```sql
select status, count(*) from jobs group by status;
select status, count(*) from messages group by status;
select name, count(*) from audit_log group by name order by 2 desc;
select count(*) filter (where resolved_at is not null) as resolved, count(*) from questions;
```

`messages` rows stuck in `pending` mean the dispatcher or the MAX API is failing; read
`last_error`.

Check the cabinet headers over HTTPS:

```bash
curl -sI https://$HOST/ | grep -iE 'content-security-policy|x-frame|x-content-type|referrer'
```

`apps/admin/nginx.conf` sends a policy with no `unsafe-inline` for scripts, `frame-ancestors
'none'`, `nosniff` and `no-referrer`. If any of them is missing, a proxy in front of the container
is stripping headers: fix that before handing the cabinet to recruiters. The session cookie is
`Secure`, so a plain-HTTP host silently loses the login.

## Rollback

Redeploy the previous image tag:

```bash
gh workflow run deploy.yml -f sha=<previous-sha>
```

Do not roll back migrations in production; ship a forward fix. The subscription stays valid because
the URL does not change.

## Backup

The daily timer runs `scripts/backup.sh`; see [backup.md](backup.md). A deploy does not replace a
backup policy: verify the timer and one restore drill before the first real employee.

## Post-deploy

Record the version and the smoke result in `docs/measurements/` if the deploy changes a measured
number. If something broke, write `docs/incidents/` the same day.
