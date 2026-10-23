# 0019 — Jev is a classifier profile, not a special case

Date: 2026-10-24
Status: accepted — the structure shipped and the classifier was measured through OpenRouter
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

### Two surfaces, one adapter

Jev is also served through OpenRouter at `POST /api/v1/systemone`, which is the same path this
adapter already builds from `JEV_BASE_URL`, so the switch is configuration and not code:
`JEV_BASE_URL=https://openrouter.ai/api/v1`, `JEV_API_KEY` as the OpenRouter key, and
`CLASSIFY_PROFILE=openrouter-jev-1.14` (model `typesafe/jev-1.14`). OpenRouter reports the charge
per call in `usage.cost`, in USD. The profile price stays `0` rather than converting dollars at an
invented exchange rate, and the run reports `cost_usd_total` and `priced_calls` from the provider's
own number. A ruble price is still the only honest way to price the direct endpoint, which reports
tokens and nothing else.

## Measured

Two runs, both on the test split with three repetitions per case. The first used the original
58 cases; the second widened the crisis and `unknown` strata to 114 cases after discovering that
the first could not support the claim it seemed to make.

### First pass, 58 cases, rubric v1

`docs/measurements/2026-10-23-sentiment-jev.md`, commit `4e8901f`:

| provider | `sentiment_accuracy` | `escalation_recall` | `false_alarm_rate` | `tag_f1` | `fallback_rate` | `p95_latency_ms` | `cost_usd_per_1k_calls` |
|---|---|---|---|---|---|---|---|
| `keyword` | 0.345 | 0.600 | 0.188 | 0.694 | 0 | 0 | 0 |
| `prompt` (`opencode-deepseek-v4.1-flash`, one repetition) | 0.741 | 0.700 | 0.375 | 0.770 | 0.224 | 4701 | not in the profile |
| `jev` (`typesafe/jev-1.14`) | 0.833 | 1.000 | 0.396 | 0.637 | 0 | 525 | 0.0432 |

The obvious reading — Jev escalates every crisis, the prompt path misses three — was wrong, and the
paired bootstrap against the prompt run said so (`delta +0.086`, 95% CI `[-0.05, 0.22]`,
`p = 0.129`). The escalation advantage rested on ten crisis cases with three discordant pairs:
`p = 0.25` by an exact sign test. A number that weak is not a finding.

### Second pass, 114 cases, rubric v1 and v2

`docs/measurements/2026-10-23-sentiment-jev-expanded-v{1,2}.md` and
[`2026-10-23-sentiment-prompt-expanded.md`](../measurements/2026-10-23-sentiment-prompt-expanded.md),
all at commit `460d91f`, which holds the widened set and rubric v2 together. 34 crisis cases,
14 `unknown`, 342 calls per provider, no fallbacks on either Jev run.

| provider | `sentiment_accuracy` (per call) | `case_accuracy` (majority) | `escalation_recall` | `false_alarm_rate` | `tag_f1` | `fallback_rate` | `p95_latency_ms` | `cost_usd_per_1k_calls` |
|---|---|---|---|---|---|---|---|---|
| `prompt` | 0.848 | 0.904 | 0.912 | 0.371 | 0.691 | 0.170 | 3078 | not in the profile |
| `jev`, rubric v1 | 0.877 | 0.877 | 0.971 | 0.338 | 0.587 | 0 | 493 | 0.0430 |
| `jev`, rubric v2 | 0.883 | 0.886 | 0.971 | 0.338 | 0.626 | 0 | 520 | 0.0430 |

Paired bootstrap over the 114 shared cases:

| comparison | delta | 95% CI | `p(delta <= 0)` | discordant pairs |
|---|---|---|---|---|
| `case_accuracy`, Jev v2 vs prompt | −0.018 | [−0.088, +0.053] | 0.729 | 1 / 0 |
| `case_accuracy`, Jev v2 vs v1 | +0.009 | [+0.000, +0.026] | 0.372 | 1 / 0 |
| `escalation_recall`, Jev v2 vs prompt | +0.059 | [−0.059, +0.176] | 0.223 | 3 swapped / 1 swapped |

Every interval contains zero. The honest statement is therefore: **on this set the two providers
are indistinguishable on quality**, and the earlier "Jev escalates every crisis" was ten cases of
luck. Jev misses `crisis-quit-direct` (one call in three came back `neutral`); the prompt path
misses the two humiliation cases and `workload-crisis-cant`, where its three calls returned
`unknown` and fell back to keywords.

What does separate them is not accuracy: Jev is 5.9 times faster at the tail, never degrades to
keywords, and costs 4.3 cents per thousand calls. The prompt path is slower, and one call in six
goes to keywords, whose own accuracy on this set is 0.345.

The tag fix came from data, not from a hunch. On the dev split the raw `noul` probabilities of 49
cases said the 0.5 threshold bought 0.590 precision for 0.767 recall, and 0.70 bought 0.754
precision at the same recall. `docs/prompts/sentiment-jev/v2.yaml` changes that number and nothing
else. On the held-out test split the gain shrank to `tag_f1 0.587 -> 0.626`: a dev-tuned threshold
transfers, but not fully, and the gap between 0.760 on dev and 0.626 on test is what overfitting
looks like before it is obvious.

The run also caught a contract defect that mocked tests could not: the live API rejects
`criteria` as a list with `400 invalid_type, expected record`. The schema and rubric v1 said list;
the payload said record. Fixed in `4e8901f` — the criteria record is now the option-to-meaning map,
which is also where the per-option wording belongs. Nothing had been measured against the wrong
shape, so v1 was corrected in place rather than superseded.

## Consequences

- A new classifier model is one YAML file plus a rubric and an eval run. No branch in
  `container.py`, no constant in an adapter.
- A rubric wording change is `v2.yaml` plus `SENTIMENT_RUBRIC=sentiment-jev@2`; the code path does
  not change, and the audit event names the version that ran.
- A Jev outage now costs at most one `timeout_s` per answer instead of `timeout_s × (retries + 1)`,
  and a dead endpoint opens the shared breaker.
- One fallback policy, one set of limits (`MAX_TAGS`, `MAX_ANSWER_CHARS`) shared with the prompt
  classifier. The sentiment contract's `maxItems` and the code constant are pinned by a test.
- The eval runner reports `cost_rub_per_1k_calls` from the classifier's own usage, which is one of
  the two questions ADR 0011 said adoption depends on. It stays `0` until a price is committed to
  the profile.
- Breaking change for an existing deployment: `SENTIMENT_PROVIDER=jev` now needs
  `CLASSIFY_PROFILE` (or an explicit `SENTIMENT_RUBRIC`), because the rubric selector is data and
  the adapter no longer carries a version. `JEV_TIMEOUT_S` and `JEV_MAX_RETRIES` become overrides
  of the profile rather than the only source, and `JEV_MODEL` is new. `.env.example` states it.
- `SENTIMENT_PROVIDER` still defaults to `prompt`, and the measurement supports keeping it: no
  interval separates the providers on quality, so flipping the default would be taste dressed as
  evidence. The case for Jev is operational — tail latency, a fallback rate of zero against 0.17,
  and a measurable price — and that is a separate change with its own rollout.
- To actually separate the two, the set needs a bigger crisis stratum, not a new metric: at 34
  crisis cases and four discordant ones, the escalation interval is still ±0.12 wide.
- The classifier profile now names rubric v2. `jev-1.13.0` keeps v1: the tag threshold was tuned
  against 1.14 probabilities, and a threshold does not transfer between model versions without the
  same measurement.

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
