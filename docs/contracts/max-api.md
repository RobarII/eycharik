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

The Russian root CA is not in the default Python trust store. `MAX_CA_BUNDLE` points the adapter at
a PEM file; when it is unset the adapter uses the default `httpx` verification.

## Endpoints the adapter implements

| Method | Path | Purpose | Used by |
|---|---|---|---|
| `POST` | `/messages?chat_id={id}` | send a message | dispatcher |
| `PUT` | `/messages/{messageId}` | edit a message | adapter only, unused today |
| `POST` | `/uploads?type=image` | reserve a media upload URL | `MaxClient` before the first image |
| `POST` | `{upload_url}` | upload image bytes as multipart | `MaxClient` before the first image |
| `POST` | `/subscriptions` | register the webhook | `onboarding.cli subscribe` |
| `GET` | `/me` | bot identity | adapter only, unused today |

`POST /messages` body: `text` ≤ 4000 characters, `attachments` with `inline_keyboard` and/or
`image`, optional `link` for a reply. `format` is omitted; the copy is plain text.

## Images

Source: <https://dev.max.ru/docs-api/use-cases/sending-messages/media> and
<https://dev.max.ru/docs-api/methods/POST/uploads> (read 2026-10-23).

| Fact | Value |
|---|---|
| Upload | `POST /uploads?type=image` returns `url` and optionally `token` |
| Bytes | `POST` the returned `url` with `Content-Type: multipart/form-data`, one file in `data` |
| Token | the upload answer carries `photos.photoIds.token`; the adapter also accepts a top-level `token` |
| Message | `{"type": "image", "payload": {"token": "..."}}` in `attachments` |
| Reuse | one token maps to one uploaded file and may be reused for later messages |
| Processing | `400 attachment.not.ready` means the file is not processed yet; retry with backoff |
| Limits | JPG, JPEG, PNG, GIF, TIFF, BMP, HEIC; at most 50 MB and 7680 × 7680 px; at most 12 images per message |
| URL alternative | `{"type": "image", "payload": {"url": "https://..."}}` exists, but the adapter uses tokens because external hosting can disappear |

The adapter uploads each bundled asset once per process and caches the token by asset name. A
restart uploads again; the token itself is reusable, but persisting it would add a cache table for
no product value at this scale.

## Webhook

| Fact | Value |
|---|---|
| Route | `POST /webhook` on our side |
| Method | `HTTPS POST`, port 443 only, no port in the URL |
| Secret header | `X-Max-Bot-Api-Secret`, compared in constant time |
| Empty secret | `503`, so a misconfigured deployment fails loudly instead of accepting unsigned calls |
| Acknowledgement | `200` within 30 seconds, anything else is a delivery failure |
| Retries | up to 10, exponential: 60 s, 150 s, 375 s, … |
| Give-up | after 8 hours without a success the bot unsubscribes |
| Long polling | disabled while a webhook subscription is active |
| Body limit | 1 MB; larger bodies answer `413` before parsing |

## Update object

Fields we depend on: `update_type`, `timestamp` (ms), `chat_id`, `user`, `message`.

`parse_update` returns `None` for an update without a chat or sender; the route acknowledges and
ignores it. A `bot_started` update creates a run with the `EMPLOYEE_CREATED` event. `message_created`
becomes `MessageReceived`; `message_callback` becomes `ButtonPressed`; a callback payload with an
unknown shape keeps its raw button id instead of raising. Unrecognised update types are
acknowledged and dropped, so an upstream addition cannot break delivery.

The `subscribe` command defaults to `message_created,bot_started`. `update_types()` in the adapter
also lists `message_callback` and `bot_stopped`; add them to the subscription when the scenario
starts using callback buttons.

## Limits and pacing

- At most two messages per second to one dialog. `MaxClient` paces per `chat_id` with an in-process
  monotonic clock. One dispatcher process owns sending; a second sender would double the rate, so
  run one worker replica.
- One message text is at most 4000 characters; longer answers are split at sentence boundaries.
- Inline keyboards support up to 210 buttons in 30 rows; the product uses at most 3 rows of 3.

## Known gaps

- The exact `message_callback` body is not pinned by an example in the docs we read. The parser is
  defensive until a real payload is captured in `apps/api/tests/`.
- Outbound images use the documented two-step upload. Incoming files are still not accepted: the
  documents scenario explains where to send them; it does not accept them in the chat.
- `bot_stopped` is parsed as a no-op. Unsubscribing a newcomer is a product decision that has not
  been made.
