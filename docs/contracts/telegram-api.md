# Telegram Bot API contract

Everything the integration relies on, with the source of each fact. If Telegram changes a field,
this file changes in the same commit as the adapter.

Source: <https://core.telegram.org/bots/api> and <https://core.telegram.org/bots/faq> (read
2026-10-26).

## Connection

| Fact | Value |
|---|---|
| Base URL | `https://api.telegram.org/bot<token>/<method>` |
| Auth | the token is part of the URL; no `Authorization` header |
| Content type | `application/json` for every method below |
| Webhook registration | `setWebhook` with `url` and `secret_token` |
| Inbound auth | header `X-Telegram-Bot-Api-Secret-Token` on every delivery |

## Endpoints the adapter implements

| Method | Path | Purpose |
|---|---|---|
| `POST` | `sendMessage` | send a message, optional `reply_markup` |
| `POST` | `editMessageText` | rewrite a sent message |
| `POST` | `setWebhook` | registration, by hand or from a script |

`sendMessage`: `chat_id`, `text` 1–4096 characters after entity parsing, `parse_mode`
(`MarkdownV2` or `HTML`), `reply_markup` with `inline_keyboard`, `reply_to_message_id`.

`sendPhoto` (`photo` as a `file_id` or a multipart upload, `caption` up to 1024 characters) is
documented but not implemented: an `OutboundMessage` carries no image yet, so the adapter sends the
text and the keyboard. Adding it is a change to the message value first, not to this adapter.

`InlineKeyboardButton.callback_data`: a `String` of 1–64 **bytes**. Longer is an error, not a
truncation.

## Updates

| `update` field | Our event |
|---|---|
| `message.text` starting with `/start` | `EMPLOYEE_CREATED` |
| `message.text` | `MESSAGE_RECEIVED` |
| `callback_query.data` | `BUTTON_PRESSED` |
| `message.document` | `FILE_RECEIVED` (not implemented, as on MAX) |

`update_id` is the dedupe key. `message.chat.id` is the chat; `from.id` is the sender, and the two
differ in groups.

## Rate limits

Telegram documents "no more than about 30 messages per second" overall and "not more than one
message per second in a single chat". The profile sets `messages_per_second: 30` and
`per_chat_per_second: 1`, and the adapter paces on both. A `429` is `ChannelUnavailableError`: the
dispatcher backs off, and the row returns to `pending`. The `retry_after` field is not honoured — the
backoff is ours, so one code path covers every messenger.

## Differences from MAX that matter

- A bot cannot start a conversation: messaging a user who never pressed `/start` fails with
  `403: bot can't initiate conversation with a user`. This aligns with the linked-identity gate:
  the run starts from `/start`, never from us.
- `parse_mode` is a dialect. `MarkdownV2` requires escaping `_*[]()~`>#+-=|{}.!`; the renderer
  escapes, the copy stays plain.
- Edits replace `text` and `reply_markup` together; an edit that omits the markup removes it.

## Not yet captured

Payload fixtures are synthetic until a real update is captured in
`apps/api/tests/fixtures/channels/telegram/`. The same rule as `max-api.md`.
