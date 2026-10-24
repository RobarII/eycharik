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

   VK: in the community settings, add a Callback API server with the URL `https://$HOST/webhook/vk`,
   paste the secret, and enable the `message_new` and `message_event` types. VK shows a confirmation
   string on the server tab; it has to equal `VK_CONFIRMATION_CODE`. VK calls the URL with
   `{"type": "confirmation"}` and expects that string back as plain text, without a trailing
   newline, inside five seconds. The route answers the handshake before it looks at the secret,
   because VK proves the address before it will send anything.

   The VK settings page is the least reliable part of this. It shows a placeholder in the secret
   field even when a secret is stored, so the field alone proves nothing, and a scripted fill does
   not always reach VK's model, which leaves the secret empty and every event answers `401`. Ask the
   API instead of the page:

   ```bash
   # the address is confirmed when status is ok; secret_key must equal VK_WEBHOOK_SECRET
   curl -s https://api.vk.com/method/groups.getCallbackServers \
     -d group_id=$VK_GROUP_ID -d v=5.199 -d access_token=$VK_ACCESS_TOKEN

   # set or repair the secret; returns the server id
   curl -s https://api.vk.com/method/groups.editCallbackServer \
     -d group_id=$VK_GROUP_ID -d server_id=$VK_SERVER_ID -d v=5.199 \
     --data-urlencode url=https://$HOST/webhook/vk \
     --data-urlencode secret_key=$VK_WEBHOOK_SECRET \
     -d access_token=$VK_ACCESS_TOKEN

   # enabled types: message_new and message_event must be true
   curl -s https://api.vk.com/method/groups.getCallbackSettings \
     -d group_id=$VK_GROUP_ID -d server_id=$VK_SERVER_ID -d v=5.199 \
     -d access_token=$VK_ACCESS_TOKEN
   ```

   VK rotates the confirmation string without notice and keeps the old one on the page until it
   re-renders, so when «Подтвердить» keeps failing, re-read the string from a freshly loaded page and
   compare it with `VK_CONFIRMATION_CODE` before changing anything else. A `200` in the API log next
   to a failing page is not proof either way: VK records the request, and `getCallbackServers` is
   what settles it.

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

VK_WEBHOOK_SECRET=... VK_GROUP_ID=... DATABASE_URL=... \
  uv run python scripts/channel_smoke.py --channel vk \
    --base-url https://$HOST --chat-id $PEER_ID --reset
```

For VK, `--chat-id` is the `peer_id` from the audit row of a message the account sent first: a
community cannot open a conversation, so there is no id to send to until the person writes.

It walks the whole scenario, presses the first option on every keyboard, files a document where the
step expects a file, and then checks delivery, the text cap, the refusals (missing secret, wrong
secret, non-JSON, oversized body, a channel that is off), the unlinked-account rule, and
redelivery. `--branch trouble` presses the last option instead, which exercises the unhappy routes
and the risk scoring. `--scenario` picks the script to drive.

The refusals follow the channel: Telegram carries the secret in a header, so a body that is not JSON
reaches the parser and answers `400`; VK carries the secret in the body, so an unparseable body
cannot be verified at all and answers `401`.

### Proving that a run follows the person

One scenario, two messengers. `--switch-to` drives the same employee's chat on a second channel, so
the smoke proves what ADR 0019 promises instead of assuming it:

```bash
TELEGRAM_WEBHOOK_SECRET=... VK_WEBHOOK_SECRET=... VK_GROUP_ID=... DATABASE_URL=... \
  uv run python scripts/channel_smoke.py --channel vk \
    --base-url https://$HOST --chat-id $PEER_ID --group-id $GROUP_ID \
    --switch-to telegram --switch-chat-id $TELEGRAM_CHAT_ID --reset
```

Both chats must already be linked to one employee (`/admin/api/identities`), and both are written
to for real. The added checks are: a start on the other messenger moves the run there and re-asks
the current question in the new conversation; the run id, its step and its question index do not
change; an answer typed in the new messenger advances that same run; a start back on the first
messenger returns the address; and each move leaves a `channel_changed` audit row. Delivery, the
text cap and the refusals are then checked on both channels.

The run needs a linked chat: the script cannot invent a messenger account, and an unlinked one is
refused by design. Telegram is asked directly, so `api.telegram.org` must be reachable from the
host running the smoke (use `HTTPS_PROXY` when it is not). The worker needs the same proxy: with a
stale one, the scenario still advances — the run does not depend on delivery — but every outbound
row stays `pending` with `last_error` set to `ConnectError`, and the smoke reports `0/N sent`.

## Verification queries

```sql
select channel, count(*) from messages group by channel;
select channel, count(*) from runs group by channel;
select channel, count(*) from channel_identities group by channel;
select fields->>'channel' as to_channel, count(*) from audit_log
  where name = 'channel_changed' group by 1;
```

A message stuck in `pending` for one channel while others deliver means that channel's token or
rate limit, not the dispatcher: the dispatcher leases rows per channel and one failing channel does
not block the rest.

## Rolling back

Remove the channel from `CHANNELS` and restart. Its inbound route answers `404`, its queued rows stay
in `messages` untouched, and nothing is deleted. Rows for that channel resume when it is enabled
again.
