# Runbook: enable a channel

MAX is on by default. Telegram and VK are off until the environment says otherwise, because a
channel without a secret and a linked account is an open door (ADR 0019). This runbook turns one on
and proves it works.

## Preconditions

- `make check` is green and the migrations are applied: `channel_identities` exists and every
  employee has a MAX link.
- `apps/api/channel-profiles/<channel>.yaml` validates against
  `docs/contracts/channel-profile.schema.json`. `make check` covers this.
- You have the bot token and the webhook secret for the messenger, and the public hostname from
  `docs/runbooks/deploy.md`.

## Steps

1. Set the environment and restart both processes:

   ```bash
   CHANNELS=max,telegram        # the enabled set; an unknown name fails at startup
   TELEGRAM_BOT_TOKEN=...       # never in git
   TELEGRAM_WEBHOOK_SECRET=...  # the value Telegram echoes in X-Telegram-Bot-Api-Secret-Token
   ```

   For VK: `CHANNELS=max,vk`, `VK_ACCESS_TOKEN`, `VK_WEBHOOK_SECRET`, `VK_CONFIRMATION_CODE`. VK
   needs all three.

   A channel in `CHANNELS` without a webhook secret (and, for VK, without a confirmation code) is
   not registered at all: its route answers `404`, so an unfinished setup cannot accept deliveries.
   `503` from a registered route means the process lost the secret at runtime — check the
   environment, not the messenger.

2. Link the test account to an employee. Nothing else lets a stranger in:

   ```bash
   curl -X POST https://$HOST/admin/api/identities \
     -H "Authorization: Bearer $HR_TOKEN" -H "content-type: application/json" \
     -d '{"channel": "telegram", "external_id": "222", "employee_id": "1001"}'
   ```

   `external_id` is the messenger's own user id: `from.id` in Telegram, `from_id`/`user_id` in VK.
   It is not the chat id, and it is not the employee id.

3. Register the webhook.

   Telegram: the CLI calls `setWebhook` with the token and the secret from the environment.

   ```bash
   uv run python -m onboarding.cli webhook --channel telegram --url "https://$HOST/webhook/telegram"
   ```

   VK: in the community settings, set the callback URL to `https://$HOST/webhook/vk`, paste the
   secret, and set the confirmation code to the same value as `VK_CONFIRMATION_CODE`. VK calls the
   URL with `{"type": "confirmation"}` and expects the code back as plain text; the route answers it
   before it parses anything.

4. Send `/start` from the linked account. Expect: an `events` row keyed `<channel>:<id>`, a `jobs`
   row that reaches `done`, a queued message whose `channel` column is the new channel, and one
   welcome message in the messenger.

5. Send `/start` from an unlinked account. Expect `200`, no run, no message, and one audit row:

   ```sql
   select name, fields from audit_log where name = 'unlinked_channel_user' order by id desc limit 5;
   ```

## Proving a channel end to end

`scripts/channel_smoke.py` posts messenger-shaped updates to the public webhook and then reads the
database, so a green run means the whole path works: verification, identity, dedupe, the scenario,
the outbox, the adapter, and the messenger's own message id.

```bash
TELEGRAM_WEBHOOK_SECRET=... DATABASE_URL=... \
  uv run python scripts/channel_smoke.py \
    --base-url https://$HOST --chat-id $CHAT_ID --reset
```

It walks the whole scenario, presses the first option on every keyboard, files a document where the
step expects a file, and then checks delivery, the text cap, the refusals (missing secret, wrong
secret, non-JSON, oversized body, a channel that is off), the unlinked-account rule, and
redelivery. `--branch trouble` presses the last option instead, which exercises the unhappy routes
and the risk scoring. `--scenario` picks the script to drive.

The run needs a linked chat: the script cannot invent a messenger account, and an unlinked one is
refused by design. Telegram is asked directly, so `api.telegram.org` must be reachable from the
host running the smoke (use `HTTPS_PROXY` when it is not).

## Verification queries

```sql
select channel, count(*) from messages group by channel;
select channel, count(*) from runs group by channel;
select channel, count(*) from channel_identities group by channel;
```

A message stuck in `pending` for one channel while others deliver means that channel's token or
rate limit, not the dispatcher: the dispatcher leases rows per channel and one failing channel does
not block the rest.

## Rolling back

Remove the channel from `CHANNELS` and restart. Its inbound route answers `404`, its queued rows stay
in `messages` untouched, and nothing is deleted. Rows for that channel resume when it is enabled
again.
