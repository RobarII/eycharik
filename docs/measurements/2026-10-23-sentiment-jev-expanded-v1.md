# Sentiment eval — jev

- command: `python -m onboarding.evals.sentiment --provider jev --split test --repeat 3`
- commit: `460d91f`
- environment: `local`
- split: `test`
- model: `typesafe/jev-1.14`
- rubric: `sentiment-jev@1`
- cases: 114 (dev 0, test 114)
- repetitions per case: 3
- calls: 342

## Quality

| metric | value | 95% CI |
|---|---|---|
| `sentiment_accuracy` | 0.877 | [0.84, 0.91] |
| `case_accuracy` | 0.877 | majority over repetitions |
| `sentiment_macro_f1` | 0.807 | — |
| `tag_precision` | 0.488 | — |
| `tag_recall` | 0.738 | — |
| `tag_f1` | 0.587 | — |
| `escalation_recall` | 0.971 | [0.92, 0.99] |
| `false_alarm_rate` | 0.338 | — |
| `fallback_rate` | 0.000 | — |
| `format_error_rate` | 0.000 | — |

## Cost

| metric | value |
|---|---|
| `cost_rub_total` | 0.0000 |
| `cost_rub_per_1k_calls` | 0.0000 |
| `input_tokens_total` | 350028 |
| `cost_usd_total` | 0.014701 |
| `cost_usd_per_1k_calls` | 0.042986 |
| `priced_calls` | 342 / 342 |

## Latency

| metric | value |
|---|---|
| `p50_latency_ms` | 320.1 |
| `p95_latency_ms` | 492.6 |
| `p99_latency_ms` | 570.2 |

## Recall per tone

| tone | recall | expected cases |
|---|---|---|
| `positive` | 0.864 | 66 |
| `neutral` | 0.643 | 42 |
| `negative` | 0.953 | 192 |
| `unknown` | 0.786 | 42 |

## Confusion matrix

Rows are the label, columns are the prediction.

| label \ predicted | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 57 | 6 | 3 | 0 |
| `neutral` | 9 | 27 | 0 | 6 |
| `negative` | 0 | 9 | 183 | 0 |
| `unknown` | 6 | 3 | 0 | 33 |

## Recall per tag

| tag | recall | expected cases |
|---|---|---|
| `access` | 0.917 | 36 |
| `manager` | 0.538 | 78 |
| `colleagues` | 1.000 | 42 |
| `workload` | 0.882 | 51 |
| `clarity` | 0.941 | 51 |
| `hr` | 0.784 | 51 |
| `it` | 1.000 | 24 |
| `integration` | 0.238 | 21 |
| `other` | 0.000 | 24 |

## Unstable cases

A case whose verdict changed between repetitions. A gate cannot be tighter than this.

| case | verdicts |
|---|---|
| `crisis-quit-direct` | negative, neutral |
| `workload-overtime-every-day` | negative, neutral |

## Missed escalations

A recruiter should have been alerted and was not. This list outranks every average.

| case | expected tone | predicted tone | tags |
|---|---|---|---|
| `crisis-quit-direct` | negative | negative | hr |

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
| `edge-calm-no-complaint` | neutral | positive | workload |
| `edge-long-mixed` | negative | negative | access, clarity, colleagues |
| `edge-injection` | negative | negative | access, it, hr |
| `other-facts-neutral` | neutral | neutral | access |
| `unknown-off-topic` | unknown | positive | clarity |
| `unknown-one-word-negative` | neutral | unknown | workload |
| `crisis-quit-plan` | negative | negative | hr |
| `crisis-quit-direct` | negative | negative | hr |
| `crisis-quit-soft-thanks` | negative | negative | integration |
| `crisis-quit-probation` | negative | negative | integration |
| `crisis-quit-vacancies` | negative | negative | integration |
| `crisis-discrimination-age` | negative | negative | integration, hr |
| `crisis-discrimination-gender` | negative | negative | colleagues, integration, hr |
| `crisis-deception-overtime` | negative | negative | workload |
| `crisis-salary-missing` | negative | negative | colleagues |
| `crisis-salary-half` | negative | negative | clarity |
| `crisis-health-hospital` | negative | negative | colleagues |
| `crisis-shouting-meeting` | negative | negative | colleagues, integration |
| `unknown-offtopic-weather` | unknown | neutral | clarity |
| `unknown-offtopic-football` | unknown | positive | workload |
| `unknown-offtopic-cafe` | unknown | unknown | clarity |
| `neutral-no-complaint` | neutral | positive | workload |
| `neutral-salary-facts` | neutral | unknown | hr |
| `positive-mentor-explained` | positive | positive | colleagues, clarity, it |
| `positive-integration-fast` | positive | positive | colleagues |
| `negative-vpn-drops` | negative | negative | it |
| `crisis-conflict-departments` | negative | negative | colleagues |

