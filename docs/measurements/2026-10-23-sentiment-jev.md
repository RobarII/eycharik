# Sentiment eval — jev

- command: `python -m onboarding.evals.sentiment --provider jev --split test --repeat 3`
- commit: `4e8901f`
- environment: `local`
- split: `test`
- model: `typesafe/jev-1.14`
- rubric: `sentiment-jev@1`
- cases: 58 (dev 0, test 58)
- repetitions per case: 3
- calls: 174

## Quality

| metric | value | 95% CI |
|---|---|---|
| `sentiment_accuracy` | 0.833 | [0.77, 0.88] |
| `case_accuracy` | 0.828 | majority over repetitions |
| `sentiment_macro_f1` | 0.705 | — |
| `tag_precision` | 0.533 | — |
| `tag_recall` | 0.792 | — |
| `tag_f1` | 0.637 | — |
| `escalation_recall` | 1.000 | [0.89, 1.00] |
| `false_alarm_rate` | 0.396 | — |
| `fallback_rate` | 0.000 | — |
| `format_error_rate` | 0.000 | — |

## Cost

| metric | value |
|---|---|
| `cost_rub_total` | 0.0000 |
| `cost_rub_per_1k_calls` | 0.0000 |
| `input_tokens_total` | 178965 |
| `cost_usd_total` | 0.007517 |
| `cost_usd_per_1k_calls` | 0.043198 |
| `priced_calls` | 174 / 174 |

## Latency

| metric | value |
|---|---|
| `p50_latency_ms` | 348.2 |
| `p95_latency_ms` | 524.6 |
| `p99_latency_ms` | 831.8 |

## Recall per tone

| tone | recall | expected cases |
|---|---|---|
| `positive` | 0.812 | 48 |
| `neutral` | 0.625 | 24 |
| `negative` | 0.917 | 96 |
| `unknown` | 0.500 | 6 |

## Confusion matrix

Rows are the label, columns are the prediction.

| label \ predicted | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 39 | 6 | 3 | 0 |
| `neutral` | 6 | 15 | 0 | 3 |
| `negative` | 0 | 8 | 88 | 0 |
| `unknown` | 3 | 0 | 0 | 3 |

## Recall per tag

| tag | recall | expected cases |
|---|---|---|
| `access` | 1.000 | 24 |
| `manager` | 0.692 | 39 |
| `colleagues` | 1.000 | 21 |
| `workload` | 0.900 | 30 |
| `clarity` | 0.917 | 36 |
| `hr` | 0.875 | 24 |
| `it` | 1.000 | 15 |
| `integration` | 0.200 | 15 |
| `other` | 0.000 | 12 |

## Unstable cases

A case whose verdict changed between repetitions. A gate cannot be tighter than this.

| case | verdicts |
|---|---|
| `workload-overtime-every-day` | negative, neutral |

## Label failures

| case | expected | got | tags |
|---|---|---|---|
| `it-new-laptop` | positive | neutral | it, access |
| `access-week-late` | negative | neutral | access, hr, it |
| `manager-neutral-intro` | neutral | neutral | colleagues, integration |
| `colleagues-buddy` | positive | positive | colleagues, integration, clarity |
| `workload-ok` | neutral | positive | workload, clarity |
| `workload-overtime-every-day` | negative | neutral | workload |
| `workload-night` | negative | neutral | colleagues |
| `clarity-goals-ok` | positive | neutral | clarity, manager |
| `hr-salary-late` | negative | negative | colleagues |
| `hr-paperwork` | positive | negative | hr |
| `integration-smooth` | positive | positive | colleagues |
| `integration-no-owner` | negative | negative | colleagues, clarity, it |
| `integration-blocked` | negative | negative | access, it, workload |
| `integration-process-unclear` | negative | negative | clarity, colleagues |
| `edge-sarcasm` | negative | negative | workload, colleagues |
| `edge-calm-no-complaint` | neutral | positive | workload, clarity |
| `edge-long-mixed` | negative | negative | access, clarity, colleagues |
| `edge-injection` | negative | negative | access, it |
| `other-facts-neutral` | neutral | neutral | access |
| `unknown-off-topic` | unknown | positive | clarity |
| `unknown-one-word-negative` | neutral | unknown | workload |
| `crisis-quit-plan` | negative | negative | hr |

