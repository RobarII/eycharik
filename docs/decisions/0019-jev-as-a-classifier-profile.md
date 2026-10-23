# 0019 — Jev is a classifier profile, not a special case

Date: 2026-10-28
Status: proposed — the structure shipped, quality still unmeasured (no `JEV_API_KEY`)
Supersedes: 0011 (partially: model selection, envelope, and prices leave the adapter)

## Context

ADR 0011 added Jev behind `SENTIMENT_PROVIDER=jev` and got the layering right: one port, a
versioned rubric, strict parsing, and a keyword fallback. Reviewed against the rules this
repository already applies to every other model call, four things were out of place:

- **No profile.** ADR 0013 moved model identity, envelope, and prices out of code and into
  `apps/api/model-profiles/<role>/<name>.yaml`. Jev kept its model inside the rubric file, its
  timeouts in `Settings`, and its price nowhere. A second classifier would have needed another
  branch in `container.py`.
- **A version in code.** `RUBRIC_VERSION = 1` and `version != 1` meant a rubric v2 is a code
  change, which is exactly what ADR 0004 forbids for prompts. The file path was also written out
  twice (`container.py`, `evals/sentiment.py`).
- **A private envelope.** Jev called `httpx` itself: no circuit breaker, no shared backoff, no
  usage accounting. A dead endpoint cost three timeouts per answer (`8 s × 3`), sequentially, in
  the risk radar loop. The chat path opens a breaker and fails fast on the same outage.
- **Two fallback copies.** `_fallback` (audit + `keyword_signal`) existed in both classifiers, and
  `MAX_TAGS`, `_TAGS`, and the 2000-character cap were duplicated. A change to the fallback policy
  had two homes.

None of this changes a single label. That is why it is a structure ADR, not a quality one.

## Decision

Jev becomes the first model with `role: classify`:

- `apps/api/model-profiles/classify/<name>.yaml` holds the model, the rubric reference
  (`sentiment-jev@1`), the envelope (`timeout_s`, `max_retries`), and the input price. The schema
  branch is in
  [`contracts/model-profile.schema.json`](../contracts/model-profile.schema.json), so a wrong key
  stops the process at startup.
- `SENTIMENT_RUBRIC` overrides the rubric reference; `CLASSIFY_PROFILE` selects the profile. With
  neither set, the adapter builds an in-memory profile named `env` from `JEV_MODEL` and friends,
  the same migration path ADR 0013 gave the other roles.
- The rubric is loaded by `RubricLibrary` (`apps/api/onboarding/app/llm/rubric.py`), validated
  against
  [`contracts/jev-rubric.schema.json`](../contracts/jev-rubric.schema.json), then checked for the
  meaning a schema cannot express: the `sentiment` question is a `choice` over the `Sentiment`
  enum, and every `tag_*` question names a `SignalTag`. The version comes from the file and the
  selector, never from a constant.
- `apps/api/onboarding/app/llm/transport.py` owns the retry matrix, the circuit breaker, and one
  deadline for the whole call. The gateway and the classifier both use it, so "provider down"
  means the same thing on both paths: one bounded wait, then the safe fallback.
- `apps/api/onboarding/app/llm/fallback.py` owns the keyword fallback, the shared limits, and the
  audit event. Both classifiers call it, so the two paths cannot drift.
- `build_sentiment()` in `apps/api/onboarding/app/llm/sentiment.py` is the only place that chooses
  a classifier. The container and the eval runner call it; neither knows a rubric path.

Cost accounting now flows: the `sentiment_classified` audit event carries `model`, `rubric`,
`input_tokens`, `latency_ms`, and `cost_rub`. The eval artifact header names the model, the rubric,
and the prompt version instead of hard-coding `rubric_version: 1`, and `--from-artifact` reads them
back.

## Measured

Nothing new. No `JEV_API_KEY` exists in this environment, and a structure change is not a quality
result. The rubric contract, the retry matrix, the breaker, and the cost arithmetic are covered by
tests against a mocked endpoint, which proves the contract, not the classifier.

The Jev row in ADR 0011 stays empty until `make eval-sentiment PROVIDER=jev SPLIT=test REPEAT=3`
runs with a key and writes `docs/measurements/<date>-sentiment-jev-<profile>.md`.

## Consequences

- A new classifier model is one YAML file plus a rubric and an eval run. No branch in
  `container.py`, no constant in an adapter.
- A rubric wording change is `v2.yaml` plus `SENTIMENT_RUBRIC=sentiment-jev@2`; the code path does
  not change, and the audit event names the version that ran.
- A Jev outage now costs at most one `timeout_s` per answer instead of `timeout_s × (retries + 1)`,
  and a dead endpoint opens the shared breaker.
- One fallback policy, one set of limits (`MAX_TAGS`, `MAX_ANSWER_CHARS`) shared with the prompt
  classifier. The sentiment contract's `maxItems` and the code constant are pinned by a test.
- The eval runner can finally report price per case, which is one of the two questions ADR 0011
  said adoption depends on.
- Breaking change for an existing deployment: `SENTIMENT_PROVIDER=jev` now needs
  `CLASSIFY_PROFILE` (or an explicit `SENTIMENT_RUBRIC`), because the rubric selector is data and
  the adapter no longer carries a version. `JEV_TIMEOUT_S` and `JEV_MAX_RETRIES` become overrides
  of the profile rather than the only source, and `JEV_MODEL` is new. `.env.example` states it.
- `SENTIMENT_PROVIDER` still defaults to `prompt`. Jev remains off until measured.

## Alternatives

- Keep the adapter's own envelope and only add a breaker — rejected: two retry policies, two
  deadlines, two places to fix the next outage.
- Put Jev inside `GatewayLLM` as a second family — rejected: Jev answers typed probabilities, not
  `choices[0].message.content`; a gateway branch on response shape is the special case this ADR
  removes.
- Let the rubric carry the model — rejected: the model is a deployment fact with a price, and it
  belongs where every other model lives.
- Version the rubric in code (`RUBRIC_VERSION = 2`) — rejected: that is a code change for a
  wording change, and it makes a measurement ambiguous about which file ran.
