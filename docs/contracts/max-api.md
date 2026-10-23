# MAX Bot API contract

Everything the integration relies on, with the source of each fact. If MAX changes a field, this
file changes in the same commit as the adapter.

Source: <https://dev.max.ru/docs-api> (read 2026-10-23).

## Connection

| Fact | Value |
|---|---|
| Base URL | `https://platform-api2.max.ru` (not `platform-api.max.ru`) |
| Auth | header `Authorization: <access_token>`; query-parameter tokens are no longer supported |
| Content type | `application/json` |
| TLS | trusted public CAs and the Russian Ministry of Digital Development root CA; self-signed is rejected |
| Token source | bot settings on the platform, or the "MAX для бизнеса" bot |

The Russian root CA is not in the default Python trust store. The adapter builds its SSL context
from `MAX_CA_BUNDLE` when set, otherwise from the system default.

## Endpoints used

| Method | Path | Purpose | Notes |
|---|---|---|---|
| `POST` | `/messages?user_id={id}` or `?chat_id={id}` | send a message | `text` ≤ 4000 chars; `attachments` with `inline_keyboard`; `format` is `markdown` or `html` |
| `PUT` | `/messages/{messageId}` | edit a message | used for streaming an answer in place |
| `POST` | `/subscriptions` | register the webhook | body `{url, update_types, secret}` |
| `GET` | `/me` | bot identity | startup self-check |
| `GET` | `/chats/{chatId}/members/me` | membership check | admin diagnostics |
| `GET` | `/updates` | long polling | development only; the docs say it is not for production |

## Webhook

| Fact | Value |
|---|---|
| Method | `HTTPS POST`, port 443 only, no port in the URL |
| Secret header | `X-Max-Bot-Api-Secret`, compared in constant time |
| Acknowledgement | `200` within 30 seconds, anything else is a delivery failure |
| Retries | up to 10, exponential: 60 s, 150 s, 375 s, … |
| Give-up | after 8 hours without a success the bot unsubscribes |
| Long polling | disabled while a webhook subscription is active |

## Update object

Fields we depend on: `update_type`, `timestamp` (ms), `chat_id`, `user`, `message`.
Subscribed types: `message_created`, `message_callback`, `bot_started`, `bot_stopped`.

The callback payload shape is read defensively: an unknown `payload` produces a `ButtonPressed`
event with the raw value, never an exception. Unrecognised update types are acknowledged and
ignored, so an upstream addition cannot break delivery.

## Limits and pacing

- At most two messages per second to one dialog, chat, or channel. The sender is rate-limited per
  `chat_id` and queues beyond that.
- One message text is at most 4000 characters; longer answers are split at sentence boundaries.
- Inline keyboards support up to 210 buttons in 30 rows; the product uses at most 3 rows of 3.

## Known gaps

- The exact `message_callback` body is not pinned by an example in the docs we read. Until a real
  payload is captured in `apps/api/tests/cassettes/`, callback handling stays behind the
  `MAX_CALLBACKS_ENABLED` flag and the product uses text commands and link buttons.
- File upload is a separate two-step flow; the onboarding scenario that accepts documents is
  specified in [../product/scenarios.md](../product/scenarios.md) and implemented after the first
  vertical slice.
