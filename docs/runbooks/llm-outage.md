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
4. Read the run's profile: `LLM_PROFILE` names the file, and the file states the model, the
   capabilities, and the envelope. The answer guard is the same for every profile.
5. If `SENTIMENT_PROVIDER=jev`, the classifier is on the same envelope: `CLASSIFY_PROFILE` names
   its file, the same breaker covers it, and a dead endpoint costs one `timeout_s`, not one per
   retry. Survey answers keep arriving and are labeled by `keyword_signal`; watch
   `sentiment_fallback` with `provider=jev` in `audit_log` — a spike there is the classifier, not
   the radar.

## Action

| Situation | Action |
|---|---|
| Provider 5xx or timeout | no action: one retry, then escalation with `unavailable` copy |
| Breaker open, provider healthy again | wait for the cooldown; the next call probes and closes it |
| Quota or billing | fail closed, alert the owner, never loop on a quota error |
| Sustained provider outage | the bot keeps scenarios, reminders, and the cabinet working; answers escalate |
| Wrong model id in a profile | edit `apps/api/model-profiles/answer/<name>.yaml`, run the tests, deploy |
| Model too slow for the budget | switch `LLM_PROFILE` to a faster profile after `make eval` passes |
| Model returns empty completions | set `retry_empty_completion` in the profile; if it persists, switch profiles (ADR 0010) |
| Cost looks wrong | the profile owns the prices; an override is `LLM_PRICE_*`, and a real price change is a profile commit |
| Classifier degraded to keywords | check `sentiment_fallback` reasons: `jev_unavailable` is the network, `jev_format` is the answer shape; the second one is a rubric/model defect, not an outage |

The bot must never answer from model memory when retrieval or the provider is unavailable.
Scenario steps and reminders keep working: they do not need the model.

## Recovery check

- New `answer_completed` audit rows appear with citations.
- One golden question returns a cited answer; compare with `docs/evals/`.
- Escalation rate returns to baseline within an hour.

## After

Write `docs/incidents/` with the timeline, the provider error text, and the change that prevents a
repeat.
