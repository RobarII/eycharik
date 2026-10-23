# Runbook: model provider outage

## Symptoms

- `llm_failures_total` rising, `answer_completed` absent for more than five minutes.
- Answers degrade to escalation with reason `no_sources` at a rate far above baseline.
- `readyz` reports `llm: fail`.

## Triage

1. Confirm with a direct call to the provider endpoint; do not trust the dashboard alone.
2. Check whether it is one provider or every provider: `GET /admin/diagnostics/providers`.
3. Check the circuit breaker state in the logs: `llm_circuit_state`.

## Action

| Situation | Action |
|---|---|
| Provider 5xx, second provider healthy | `LLM_PROVIDER` flips to the fallback; no restart needed |
| All providers down | answers become escalations; the bot keeps tracking scenarios and timers |
| Provider quota or billing | fail closed: escalation, alert the owner, never retry a quota error |
| Slow provider, p95 > 5 s | lower `LLM_TIMEOUT_S`, keep streaming disabled, alert |

The bot must never answer from model memory when retrieval is unavailable. Scenario steps and
reminders keep working: they do not need the model.

## Recovery check

- `llm_failures_total` stops rising.
- One golden question returns a cited answer; compare with `docs/evals/`.
- Escalation rate returns to baseline within an hour.

## After

Write `docs/incidents/` with the timeline, the provider error text, and the change that prevents a
repeat.
