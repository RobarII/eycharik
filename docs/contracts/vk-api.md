# VK Callback API contract

Everything the integration relies on, with the source of each fact. If VK changes a field, this
file changes in the same commit as the adapter.

Source: <https://dev.vk.com/ru/api/callback/getting-started> and
<https://dev.vk.com/ru/method/messages.send> (read 2026-10-26).

## Connection

| Fact | Value |
|---|---|
| Inbound | VK posts JSON to the callback URL configured for the community |
| Confirmation | a payload with `"type": "confirmation"` must be answered with the confirmation code, plain text |
| Inbound auth | the `secret` field of every payload, when a secret is configured; otherwise absent |
| Outbound | `https://api.vk.com/method/messages.send` with `access_token` and `v` |

Every event carries `type`, `group_id`, and `event_id`. `event_id` is the dedupe key.

## Endpoints the adapter implements

| Method | Purpose |
|---|---|
| `messages.send` | send a message with an optional `keyboard` and `attachment` |
| `messages.edit` | rewrite a message sent by the community |

`messages.getLongPollServer`, `photos.getMessagesUploadServer` and similar are documented but unused:
an `OutboundMessage` carries no image yet.

`messages.send`: `peer_id`, `message` up to 4096 characters, `random_id` (required: VK drops a
repeat with the same value), `keyboard` (JSON, see below), `attachment` (for images).

## Events

| Payload | Our event |
|---|---|
| `message_new`, `object.message.text` starting with `/start` | `EMPLOYEE_CREATED` |
| `message_new` | `MESSAGE_RECEIVED` |
| `message_event` (callback button) | `BUTTON_PRESSED` |

`object.message.peer_id` is the chat; `from_id` is the sender. In `message_event`, `peer_id` and
`user_id` are separate fields, and `payload` carries the button id.

VK retries a delivery that is not acknowledged with `ok` within its timeout. `event_id` plus the
`events` primary key makes the repeat harmless.

## Keyboard

`keyboard` is a JSON object: `one_time`, `inline`, and `buttons` — up to 10 rows of up to 5 buttons.
A button is `{"action": {"type": "callback", "label": "...", "payload": "..."}}`; `payload` is at
most 255 characters.

Two consequences the profile encodes:

- `keyboard_scope: dialog` — the keyboard belongs to the conversation, not to one message. Sending a
  new message without `keyboard` leaves the old one in place; removing it needs an explicit empty
  keyboard.
- `inline: true` is accepted only for messages from a community, and a callback button only fires
  when the community has callback support enabled.

## Rate limits

VK documents a per-method limit of about 20 requests per second for a community token. The profile
sets `messages_per_second: 20` and leaves `per_chat_per_second: null`: there is no documented
per-chat rule. A `429` or error code 6 (`Too many requests per second`) is `ChannelUnavailable`.

## Not yet captured

Payload fixtures are synthetic until a real callback is captured in
`apps/api/tests/fixtures/channels/vk/`. Confirm the rate limit and the `inline` restriction against
the community settings before enabling the channel in production.
