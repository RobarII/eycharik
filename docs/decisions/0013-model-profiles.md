# 0013 — A model is a profile, not a code path

Date: 2026-10-27
Status: accepted
Supersedes: 0010 (partially: model selection, envelope, and prices leave the environment)

## Context

The gateway was provider-agnostic but model-agnostic only in name. Single-model knobs lived in
three places at once:

- `GatewayLLM.__init__` stored `temperature` and prices, yet `_payload` read `request.temperature`
  and `CompletionRequest.max_tokens` defaults. `LLM_TEMPERATURE` was dead configuration: setting it
  changed nothing.
- `_payload` hard-coded the OpenAI dialect: `response_format`, `reasoning_effort`, `max_tokens`.
  A model that wants `max_completion_tokens`, or that rejects `response_format`, needed a code
  change in the gateway.
- `EMBED_DIM` was duplicated between settings and the `kb_chunks.embedding` column, and the reranker
  read its model from a separate environment variable with no record of which reranker a
  measurement used.

Every one of those is a *fact about the model*, not about the deployment. Facts that live in code
rot the first time the model changes.

## Decision

A model is described by a YAML profile, validated against
[`contracts/model-profile.schema.json`](../contracts/model-profile.schema.json):

- `apps/api/model-profiles/answer/<name>.yaml` — dialect, capabilities (`json_mode`,
  `max_tokens_field`, `reasoning_effort`), envelope (`temperature`, `max_tokens`, `timeout_s`,
  `max_retries`, `retry_empty_completion`), prices;
- `apps/api/model-profiles/embed/<name>.yaml` — dialect, model, `dim`, timeout;
- `apps/api/model-profiles/rerank/<name>.yaml` — model, timeout.

`LLM_PROFILE`, `EMBED_PROFILE`, and `RERANK_PROFILE` select a profile by file name. With them
unset, the previous environment knobs still build an equivalent in-memory profile named `env`, so
the migration is opt-in per deployment. Resolution order for every value: explicit environment
value, then the profile, then the dataclass default.

The schema is the gate. `ProfileLibrary` validates every file before use and refuses an unknown
key; a field that does not apply to the role (`dim` on an answer model, `temperature` on a
reranker) is an error, not silence. A missing or invalid profile stops the process at startup,
where a typo is a failed deploy rather than a mystery in production.

`EMBED_DIM` and the profile's `dim` must agree. A wider vector is a migration plus a reindex, not a
setting, and the loader says so by name.

Prices move into the profile and default to `0`. Cost accounting then reports `0`, never a guess;
a measured price is a commit to a profile file, reviewable like any other fact.

Prompts stay where ADR 0004 put them. A prompt is pinned to the answer contract, not to a model,
and the profile never carries prompt text.

## Consequences

- A new answer model is one YAML file plus `make eval`; no Python changes, no review of the
  gateway, no redeploy of code that differs only by a string.
- Removing a model is deleting a file. The diff shows what ran and what stopped running.
- A measurement names the profile (`model: openrouter-gpt-4.1-mini`), so "which model produced
  0.070 ₽ per answer" is answerable from the repository, not from chat history.
- Capability flags are still a fixed vocabulary. A provider that needs a genuinely different
  request shape gets a new `family` and a small adapter in `providers.py`; profiles do not grow a
  scripting language.
- The offline extractive provider remains a provider switch (`LLM_PROVIDER=extractive`), not a
  profile: it is a test double, not a model with an envelope.
- `LLM_PRICE_*`, `LLM_MAX_TOKENS`, `LLM_TIMEOUT_S`, and `LLM_MAX_RETRIES` become documented
  overrides instead of the only source. `LLM_TEMPERATURE` is deleted rather than fixed: the prompt
  owns the answer temperature (ADR 0004) and the profile owns the default for calls that do not pin
  one. The ADR 0010 cost statement still holds; the number it recorded came from a measurement, and
  the profile now states the model it belongs to.

## Alternatives

- Keep model knobs in `Settings` only — rejected: every new capability becomes a boolean flag in
  the gateway, and two models in the same deployment cannot coexist.
- One profile per deployment (profile file generated from environment) — rejected: the file would
  be a build artifact and could not be reviewed or versioned with the code.
- Prompt-per-model forks — rejected: two prompts diverge within a month, and the answer contract
  stops meaning one thing. Model differences belong in capabilities, not in wording.
