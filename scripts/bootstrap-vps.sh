#!/usr/bin/env bash
# One-time host bootstrap for the single-VM deployment. Idempotent and non-destructive: it adds a
# dedicated deploy user, a vhost, a certificate and the backup timer. It never edits the existing
# nginx sites, SSH config, or firewall.
#
# Run as root from a checkout of this repository:
#
#   DOMAIN=bot.example.com ACME_EMAIL=ops@example.com \
#   DEPLOY_PUBKEY="$(cat /tmp/onboarding_deploy.pub)" \
#   REPO_URL=git@github.com:owner/repo.git scripts/bootstrap-vps.sh
set -Eeuo pipefail
IFS=$'\n\t'

[ "$(id -u)" -eq 0 ] || { echo "run as root" >&2; exit 1; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOMAIN="${DOMAIN:-bot.state3407.space}"
ACME_EMAIL="${ACME_EMAIL:-}"
DEPLOY_USER="${DEPLOY_USER:-deploy}"
REPO_DIR="${REPO_DIR:-/opt/onboarding}"
REPO_URL="${REPO_URL:-}"
DEPLOY_PUBKEY="${DEPLOY_PUBKEY:-}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/onboarding}"

[[ "$DOMAIN" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$ ]] \
    || { echo "invalid DOMAIN: $DOMAIN" >&2; exit 1; }
[[ -z "$ACME_EMAIL" || "$ACME_EMAIL" == *@*.* ]] \
    || { echo "invalid ACME_EMAIL: $ACME_EMAIL" >&2; exit 1; }
[[ "$REPO_DIR" =~ ^/[A-Za-z0-9._/-]+$ ]] \
    || { echo "invalid REPO_DIR: $REPO_DIR" >&2; exit 1; }

log() { printf 'bootstrap: %s\n' "$*"; }

log "installing missing packages"
PACKAGES=(ca-certificates curl gettext-base nginx certbot python3-certbot-nginx git)
MISSING=()
for package in "${PACKAGES[@]}"; do
    dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q 'install ok installed' \
        || MISSING+=("$package")
done
if [ "${#MISSING[@]}" -gt 0 ]; then
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends "${MISSING[@]}"
fi

log "creating $DEPLOY_USER"
if ! id -u "$DEPLOY_USER" >/dev/null 2>&1; then
    useradd --create-home --shell /bin/bash "$DEPLOY_USER"
fi
if getent group docker >/dev/null; then
    usermod -aG docker "$DEPLOY_USER"
else
    log "docker group is missing; install Docker before the first deploy"
fi

install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" -m 0750 "$REPO_DIR"
install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" -m 0700 "$BACKUP_DIR"

if [ -n "$DEPLOY_PUBKEY" ]; then
    install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" -m 0700 "/home/$DEPLOY_USER/.ssh"
    touch "/home/$DEPLOY_USER/.ssh/authorized_keys"
    chown "$DEPLOY_USER:$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh/authorized_keys"
    chmod 600 "/home/$DEPLOY_USER/.ssh/authorized_keys"
    grep -qxF "$DEPLOY_PUBKEY" "/home/$DEPLOY_USER/.ssh/authorized_keys" \
        || printf '%s\n' "$DEPLOY_PUBKEY" >>"/home/$DEPLOY_USER/.ssh/authorized_keys"
    log "installed the CI public key for $DEPLOY_USER"
fi

if [ -n "$REPO_URL" ] && [ ! -d "$REPO_DIR/.git" ]; then
    if [ -z "$(ls -A "$REPO_DIR" 2>/dev/null || true)" ]; then
        # First contact with github.com happens here; pin it afterwards in the deploy user's
        # known_hosts. Later fetches use the normal strict check.
        sudo -u "$DEPLOY_USER" env GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new" \
            git clone "$REPO_URL" "$REPO_DIR"
        log "cloned $REPO_URL into $REPO_DIR"
    else
        log "$REPO_DIR is not empty; clone it manually as $DEPLOY_USER"
    fi
fi

if [ -f "$REPO_DIR/.env.production.example" ] && [ ! -f "$REPO_DIR/.env.prod" ]; then
    install -o "$DEPLOY_USER" -g "$DEPLOY_USER" -m 0600 \
        "$REPO_DIR/.env.production.example" "$REPO_DIR/.env.prod"
    log "created $REPO_DIR/.env.prod from the example; fill the secrets before the first deploy"
fi

log "installing the ACME vhost for $DOMAIN"
AVAIL=/etc/nginx/sites-available
ENABLED=/etc/nginx/sites-enabled
ACME_NAME=onboarding-acme.conf
FINAL_NAME=onboarding.conf
install -d -m 755 /var/www/html

BACKUP_CONF=""
if [ -f "$AVAIL/$FINAL_NAME" ]; then
    BACKUP_CONF="$(mktemp)"
    cp "$AVAIL/$FINAL_NAME" "$BACKUP_CONF"
fi
cleanup() { [ -n "$BACKUP_CONF" ] && rm -f "$BACKUP_CONF"; }
trap cleanup EXIT

envsubst '${DOMAIN}' <"$ROOT/infra/nginx/onboarding-acme.conf.template" >"$AVAIL/$ACME_NAME"
ln -sfn "../sites-available/$ACME_NAME" "$ENABLED/$ACME_NAME"
nginx -t
systemctl is-active --quiet nginx || systemctl start nginx
systemctl enable nginx >/dev/null 2>&1 || true
systemctl reload nginx

if [ ! -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    [ -n "$ACME_EMAIL" ] || { echo "ACME_EMAIL is required to issue a certificate" >&2; exit 1; }
    log "issuing a certificate for $DOMAIN"
    certbot certonly --webroot -w /var/www/html -d "$DOMAIN" \
        --non-interactive --agree-tos --email "$ACME_EMAIL" --keep-until-expiring
fi

log "installing the TLS vhost for $DOMAIN"
envsubst '${DOMAIN}' <"$ROOT/infra/nginx/onboarding.conf.template" >"$AVAIL/$FINAL_NAME"
ln -sfn "../sites-available/$FINAL_NAME" "$ENABLED/$FINAL_NAME"
rm -f "$ENABLED/$ACME_NAME"

if ! nginx -t; then
    echo "bootstrap: nginx rejected the TLS vhost; restoring the previous config" >&2
    if [ -n "$BACKUP_CONF" ]; then
        cp "$BACKUP_CONF" "$AVAIL/$FINAL_NAME"
    else
        rm -f "$AVAIL/$FINAL_NAME" "$ENABLED/$FINAL_NAME"
    fi
    nginx -t || true
    exit 1
fi
systemctl reload nginx

log "installing the backup timer"
install -m 0644 "$ROOT/infra/systemd/onboarding-backup.service" /etc/systemd/system/
install -m 0644 "$ROOT/infra/systemd/onboarding-backup.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now onboarding-backup.timer

cat <<NEXT

bootstrap: done. Remaining manual steps:
  1. DNS: A $DOMAIN -> $(curl -fsS --max-time 5 https://api.ipify.org 2>/dev/null || echo '<this host>')
  2. As $DEPLOY_USER, log in to the registry once:
       sudo -u $DEPLOY_USER docker login ghcr.io -u <github-user>
  3. Fill $REPO_DIR/.env.prod (chmod 600), then deploy the first release:
       cd $REPO_DIR && ./scripts/deploy-remote.sh <40-character-sha>
  4. Add the host key to the GitHub secret DEPLOY_KNOWN_HOSTS:
       ssh-keyscan -p 22 $DOMAIN 2>/dev/null
  5. Backups: create /etc/onboarding-backup.env with BACKUP_S3_URI, then:
       systemctl start onboarding-backup.service && journalctl -u onboarding-backup.service
  6. Check listeners and firewall before handing the host over:
       ss -lntp

NEXT
