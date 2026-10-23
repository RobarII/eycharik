# Runbook: model provider outage

## Symptoms

- Answers escalate with reason `unavailable` far above baseline.
- `answer_unavailable` and `answer_rejected` rows appear in `audit_log`; `answer_completed`
  rows keep appearing with `accepted = false`.
- p95 answer latency approaches the timeout; the breaker opens and stays open.

## Triage

1. Call the provider directly with the configured key; do not trust the bot alone.
2. Read the last `answer_unavailable` audit rows: they carry the prompt version and retrieval
   size, never the key or the question text.
3. Check the breaker: after `LLM_BREAKER_THRESHOLD` consecutive failures it opens for
   `LLM_BREAKER_COOLDOWN_S` and the gateway fails fast without a request.

## Action

| Situation | Action |
|---|---|
| Provider 5xx or timeout | no action: one retry, then escalation with `unavailable` copy |
| Breaker open, provider healthy again | wait for the cooldown; the next call probes and closes it |
| Quota or billing | fail closed, alert the owner, never loop on a quota error |
| Sustained provider outage | the bot keeps scenarios, reminders, and the cabinet working; answers escalate |
| Wrong model name | fix `LLM_MODEL`, restart the worker; no migration needed |

The bot must never answer from model memory when retrieval or the provider is unavailable.
Scenario steps and reminders keep working: they do not need the model.

## Recovery check

- New `answer_completed` audit rows appear with citations.
- One golden question returns a cited answer; compare with `docs/evals/`.
- Escalation rate returns to baseline within an hour.

## After

Write `docs/incidents/` with the timeline, the provider error text, and the change that prevents a
repeat.
