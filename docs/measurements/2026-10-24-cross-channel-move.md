# A run follows the person across messengers — 2026-10-24

- **Command**: `uv run python scripts/channel_smoke.py --base-url https://state3407.space
  --channel vk --chat-id 595879308 --group-id 242545422 --switch-to telegram
  --switch-chat-id 5596309088 --scenario onboarding_plant --reset`, then the same with
  `--channel telegram --chat-id 5596309088 --switch-to vk --switch-chat-id 595879308
  --group-id 242545422`
- **Commit**: `9a81e76` for the smoke, `fec0c20` for the API and the worker it drove
- **Date**: `2026-10-24`
- **Environment**: `local` workspace `~/moshackathon`, API on `:8010` behind the VPS nginx
  (`https://state3407.space/webhook/{channel}`), worker on the same host, Postgres in docker
  (`onboarding_tg` at `0014_channel_address`), `CHANNELS=max,telegram,vk`,
  `LLM_PROVIDER=extractive`, `EMBED_PROVIDER=hashing`
- **Dataset**: the two linked chats of one employee — VK peer `595879308` and Telegram chat
  `5596309088` — driving `onboarding_plant` (30 outbound messages on the calm branch)

## Result

| Metric | VK -> Telegram -> VK | Telegram -> VK -> Telegram | Gate | Pass |
|---|---|---|---|---|
| checks | 48/48 | 48/48 | all | yes |
| outbound rows on the other channel after a start there | 1 | 1 | > 0 | yes |
| run id and step after the move | unchanged | unchanged | unchanged | yes |
| step after an answer typed on the other channel | advanced | advanced | advanced | yes |
| `channel_changed` audit rows for the employee | 3, then 5 | 3, then 5 | >= 2 | yes |
| messages accepted by VK | 30/30 | 2/2 | 100% | yes |
| messages accepted by Telegram | 2/2 | 30/30 | 100% | yes |
| rows without a messenger id | 0 | 0 | 0 | yes |
| longest text | 222 (VK), 198 (Telegram) | same | <= 4096 | yes |
| redelivery: events / jobs / runs / messages | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 | yes |

The audit row count grows by two per run because the smoke moves the run out and back; the numbers
above are the accumulated totals in `audit_log` for one employee, not per-run deltas.

## Notes

This is the live path. Both messengers really delivered updates, and both send APIs answered `200`
for every outbound row, so the rows carry VK's and Telegram's own message ids. The scenario is
driven by text the smoke supplies, so this says nothing about answer quality.

The same run is followed in both directions, which is what makes it a proof rather than a demo:
whichever messenger the person uses, the run keeps its step and the replies go to the address they
last used. The re-ask on the new address is a second message in the new conversation, not a copy of
the old one, so a person who switches mid-step is not left without the question.

Two answers to the same step are two steps: a repeated sentence from two messengers is not deduped
(`docs/decisions/0023-a-delivery-is-deduped-not-a-sentence.md`). What this measurement pins is that
the *move* is exact; the duplicate itself is not exercised here.

The database had to be brought onto this branch's migration lineage first: a database stamped at
`0011_channel_address` from the feature branch cannot be upgraded by `main`, where the same migration
is `0014_channel_address`. See `docs/runbooks/migrate.md`.
