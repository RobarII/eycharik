# Channel contract

The boundary between the domain and a messenger. Everything here is normative; a messenger adapter
that breaks it fails `tests/test_channel_contract.py`.

Decided in [ADR 0019](../decisions/0019-a-channel-is-an-address.md). Limits per messenger live in
`apps/api/channel-profiles/<channel>.yaml`, validated by
[channel-profile.schema.json](channel-profile.schema.json).

## Values

| Value | Meaning |
|---|---|
| `Channel` | `max`, `telegram`, `vk`. A `StrEnum` in `onboarding.core.models`. |
| `Address(channel, chat_id)` | Where a conversation is. Stored on the run, the outbox row, and the question row. |
| `EmployeeId` | A person in the company directory. **Never** a messenger user id. |

A sender is mapped to an employee by `channel_identities(channel, external_id) -> employee_id`. The
webhook resolves it once, on entry. An unlinked sender is refused with an audit row
(`unlinked_channel_user`), never onboarded: the right to talk to the bot is a company fact.

## Inbound

```python
class Ingress(Protocol):
    channel: Channel
    configured: bool        # False -> the route answers 503, not 401

    def verify(self, headers: Mapping[str, str], body: bytes) -> bool:
        """True when this delivery comes from the messenger. Constant-time compare."""

    def handshake(self, body: bytes) -> str | None:
        """The plain-text answer a messenger requires before it delivers events (VK), else None."""

    def parse(self, body: bytes, *, received_at: datetime) -> InboundMessage | None:
        """A typed inbound message, or None when this update is not ours to handle."""
```

```python
@dataclass(frozen=True, slots=True)
class InboundMessage:
    dedupe_key: str          # already namespaced: "telegram:12345"
    address: Address
    sender: str              # the messenger's user id, as a string
    event: Event
    starts_run: bool         # a first contact button, not a reply
```

Rules:

1. `parse` is pure and never raises on an unknown field. A missing field degrades to `None`; an
   unknown update type returns `None`. Messengers add fields without warning.
2. `dedupe_key` is `f"{channel}:{external_event_id}"`. It is the `events` primary key, so a retried
   delivery is dropped by the database, not by application code.
3. `starts_run` is true only for a first-contact event: `bot_started` on MAX, `/start` on Telegram,
   `message_new` with a `/start` text on VK. Everything else is a reply inside an existing run.
4. `parse` does not touch the database, the clock, or the network.

## Outbound

```python
class Messaging(Protocol):
    channel: Channel

    async def send(self, message: OutboundMessage) -> str: ...
    async def edit(self, message_id: str, text: str, keyboard: Keyboard = ()) -> None: ...
```

`OutboundMessage` carries the domain message only: `address`, `text`, `image` (a name resolved by the
adapter), `keyboard` (`tuple[tuple[Button, ...], ...]`), `reply_to`. The adapter renders it; the
outbox never stores a wire payload.

Failures are two:

| Error | Meaning | Dispatcher |
|---|---|---|
| `ChannelUnavailableError` | transport failure or a 5xx | row returns to `pending` with backoff |
| `ChannelRejectedError` | a 4xx the messenger will repeat | row is parked as `failed` |

The dispatcher catches nothing else silently. An unexpected exception is a bug and is parked with
its type in `last_error`.

## Rendering

`core/channels.py` applies a profile without I/O:

- `fit_text(text, profile) -> tuple[str, ...]` splits at paragraph, then sentence boundaries, so no
  part exceeds `max_text_chars`. Every part is a separate outbox row, in order.
- `fit_keyboard(keyboard, profile) -> Keyboard` raises when the keyboard does not fit the channel
  (rows, buttons per row, callback payload bytes). A scenario that cannot be rendered on an enabled
  channel is a startup error, not a runtime surprise.

The adapter then:

- escapes the text into `profile.markup` (`none` means no escaping and no formatting);
- maps `Button.id` to the channel's callback field;
- resolves `image` by name through its own asset directory and upload flow;
- applies `profile.messages_per_second` and `profile.per_chat_per_second`.

## Delivery

At-least-once, per row: the outbox is written in the transaction that records the intent, a lease
guards a worker that dies mid-send, and a parked row is visible with `last_error`.

Pending rows are grouped by channel and delivered concurrently, so a 2 msg/s messenger cannot slow a
30 msg/s one. Pacing is inside the adapter, one limiter per channel, not one per process.

## Adding a channel

1. `docs/contracts/<channel>-api.md` — the facts the adapter relies on, each with a source URL.
2. `apps/api/channel-profiles/<channel>.yaml`, passing `channel-profile.schema.json`.
3. `apps/api/onboarding/app/channels/<channel>/{client,ingress,render}.py`.
4. A settings block: token, secret, base URL. Every secret is a `SecretStr` and appears in no log.
5. Entries in the composition root: the `Ingress` in `ingress`, the `Messaging` in `senders`.
6. Contract tests: `tests/test_channel_contract.py` covers the adapter by parameter; payload
   fixtures live in `tests/fixtures/channels/<channel>/` and are captured, not invented.
7. A row in `docs/README.md`, and the channel in the "Building blocks" of `docs/architecture.md`.

Nothing else changes. `core/`, prompts, retrieval, evals, and the cabinet are channel-neutral.
