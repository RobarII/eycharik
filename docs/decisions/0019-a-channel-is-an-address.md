# 0019: A channel is an address, not a client

- Status: accepted
- Date: 2026-10-26
- Amends: the "MAX is the only client" sentence of `docs/architecture.md`

## Context

The product was built against one messenger, and the code says so in three places that are not about
messengers at all:

- `MessageRow.chat_id` is a bare number, so the dispatcher cannot know which API to call.
- `EmployeeId` is the messenger's user id (`EmployeeId(str(inbound.user_id))` in the webhook), so a
  person in two messengers is two employees with two runs.
- `MAX_MESSAGE_CHARS = 4000` sits in `core/models.py`, which is the domain, not MAX.

Everything else is already channel-agnostic: `ports.Messaging`, the abstract `Keyboard`, the
transactional outbox, the pure transition engine, retrieval, prompts, and the cabinet, which never
speaks to a messenger (invariant 9). The cost of a second channel is therefore transport, not
behaviour.

Telegram and VK were requested. Reading the three APIs, the differences that matter are not the
endpoint names:

| | MAX | Telegram | VK |
|---|---|---|---|
| inbound auth | `X-Max-Bot-Api-Secret` | `X-Telegram-Bot-Api-Secret-Token` | `secret` field in the body + a confirmation handshake |
| button callback | inline keyboard, `payload` per button | inline keyboard, `callback_data` ≤ 64 bytes | keyboard is dialog-scoped, `payload` per button |
| text limit | 4000 | 4096 | 4096 |
| pacing | 2 msg/s per chat | ~30 msg/s overall, ~1 msg/s per chat | ~20 req/s per method |

A `switch channel` inside one client would make every one of those a branch in the hot path.

## Decision

**The channel is a value in the domain; the API is an adapter.**

1. `core/models.py` gains `Channel` (a `StrEnum`) and `Address(channel, chat_id)`. `ChatId` stays;
   `Address` is what the run, the outbox and the question log store.
2. `EmployeeId` stops being a messenger user id. A new table `channel_identities(channel,
   external_id) -> employee_id` maps a sender to an employee, and the webhook resolves it once, on
   entry. An unlinked sender is refused, not onboarded: access is a corporate fact, not a chat fact.
3. Inbound is a port. `ports.Ingress` is `channel`, `verify(headers, body)`, `handshake(body)`,
   `parse(body, received_at) -> InboundMessage | None`. The adapter fills `dedupe_key` already
   namespaced (`telegram:12345`), so `events.key` needs no schema change.
4. Outbound keeps one port, but `Messaging` raises the two errors the dispatcher can act on:
   `ChannelUnavailable` (retry later) and `ChannelRejected` (a retry will not help). A blanket
   `except Exception` in the dispatcher becomes a classification.
5. Limits and shapes are data. `docs/contracts/channel-profile.schema.json` describes a channel
   profile; `apps/api/channel-profiles/<channel>.yaml` holds one per messenger. `core/channels.py`
   reads that profile and provides the two pure functions that apply it: `fit_text` (split at
   sentence boundaries, as `max-api.md` already promised) and `fit_keyboard` (reject a keyboard the
   channel cannot carry). No messenger name appears in `core/` beyond `Channel`.
6. Adapters live in `apps/api/onboarding/app/channels/<channel>/` with three files: `client.py`
   (wire), `ingress.py` (payload to `Event`), `render.py` (domain `Keyboard` to the wire shape).
   `app/max/` moves there unchanged in behaviour.
7. One webhook route. `POST /webhook/{channel}` looks the ingress up in the composition root and
   does the same six things for everybody: verify, limit, handshake, parse, dedupe, enqueue.

## Consequences

- Channel neutrality: `core/`, prompts, retrieval and every eval stay untouched by a new channel.
  A new messenger is a profile file, one adapter, and a contract test.
- The outbox stores the domain message, never the wire payload: text, image name, and a keyboard of
  `Button(id, text)`. Rendering happens in the adapter, so a message that is already in the table
  can be re-rendered after a channel bug fix.
- One active run per employee becomes cross-channel, which is the correct rule: a person is
  onboarded once, not once per app. The run follows the person: an answer from another linked
  messenger is answered there, the run's address moves, and the move is audited as
  `channel_changed`.
- The dispatcher must not let a slow channel block a fast one. Pending rows are grouped by channel
  and delivered concurrently; pacing stays per adapter.
- `MAX_MESSAGE_CHARS` remains as the domain cap for a scenario message, and a channel profile may
  lower it. A profile may not raise it: the domain cap is what the strictest supported channel can
  carry.
- Tests stop needing a messenger. A `FakeChannel` adapter implements `Messaging` and `Ingress`; the
  service tests never mention MAX again. A parametrised contract test asserts that every adapter
  answers the same domain events for the same domain message.

## Alternatives rejected

- **One `UniversalClient` with `if channel == ...`.** Every difference becomes a branch in the send
  path, and the branches are the least tested code. Rejected.
- **A channel column on the outbox and nothing else.** Cheaper for one week and it leaves
  `EmployeeId` meaning two different things, so identity, escalation and retention stay wrong.
- **A separate service per messenger.** Three deployments, three databases, and the run state would
  have to be synchronised. The whole point of the single Postgres ADR (0005) is that it is not.
- **Per-channel copy.** The same sentence in three files drifts. Copy stays one file; only the
  markup dialect differs, and that is the renderer's job.
- **Trusting the messenger for identity (user id = employee id).** That is what made the second
  channel impossible. An explicit link table is also the access-control gate.
