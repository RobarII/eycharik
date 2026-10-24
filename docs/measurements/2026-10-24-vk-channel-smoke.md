# VK channel smoke — 2026-10-24

- **Command**: `uv run python scripts/channel_smoke.py --channel vk --base-url https://state3407.space --chat-id 595879308 --group-id 242545422 --scenario onboarding_plant --reset`
  and `... --scenario onboarding_default --branch trouble --reset`
- **Commit**: `03a8d19`
- **Date**: `2026-10-24`
- **Environment**: `local` workspace `~/moshackathon-channels`, API on `:8010` behind the VPS nginx
  (`https://state3407.space/webhook/vk`), worker on the same host, Postgres in docker
  (`onboarding_tg`), `CHANNELS=max,telegram,vk`, `LLM_PROVIDER=extractive`,
  `EMBED_PROVIDER=hashing`
- **Dataset**: the two active scenarios — `onboarding_plant` (calm branch, 30 outbound messages) and
  `onboarding_default` (trouble branch, 32 outbound messages)

## Result

| Metric | Value | Gate | Pass |
|---|---|---|---|
| checks, calm branch | 38/38 | 38/38 | yes |
| checks, trouble branch | 40/40 | 40/40 | yes |
| messages accepted by VK | 30/30 and 32/32 | 100% | yes |
| messages without a VK message id | 0 | 0 | yes |
| longest text | 222 chars | <= 4096 | yes |
| risk assessments, trouble branch | 15 | > 0 | yes |
| refusals: missing secret, wrong secret | 401, 401 | 401 | yes |
| refusals: non-JSON body | 401 | 401 (VK verifies from the body) | yes |
| refusals: oversized body | 413 | 413 | yes |
| unknown channel | 404 | 404 | yes |
| unlinked sender | 200, 0 runs, 1 audit row | 200, no run | yes |
| redelivery: events / jobs / runs / messages | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 | yes |

The redelivery row is a separate probe: the same `event_id` posted twice to
`https://state3407.space/webhook/vk`, both answered `200`, then counted in the database.

## Notes

This is the live path, not the offline one: VK really delivered `message_new` and `message_event`,
and `messages.send` really returned `200` for every outbound row, so the rows carry VK's own message
ids. It says nothing about answer quality — the provider is `extractive` on purpose, and the
scenario is driven by text the smoke supplies.

One calm run reported 37/38 before these two. The failing check was not captured, and both reruns
were clean, so a single step settle is the suspect: `SETTLE_SECONDS` is 25, which is thin for a step
whose outbound message the worker sends over the network. Do not compare this against the eval
numbers in the other measurements; they measure retrieval and generation, this measures a channel.

Prerequisite worth repeating: the worker needs the same proxy the API has. With a stale one the
scenario still advances — the run does not wait for delivery — and the smoke reports `0/30 sent`
with `last_error = ConnectError` on every row.
