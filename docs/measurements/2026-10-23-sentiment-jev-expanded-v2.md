# Sentiment eval — jev

- command: `python -m onboarding.evals.sentiment --provider jev --split test --repeat 3`
- commit: `460d91f`
- environment: `local`
- split: `test`
- model: `typesafe/jev-1.14`
- rubric: `sentiment-jev@2`
- cases: 114 (dev 0, test 114)
- repetitions per case: 3
- calls: 342

## Quality

| metric | value | 95% CI |
|---|---|---|
| `sentiment_accuracy` | 0.883 | [0.84, 0.91] |
| `case_accuracy` | 0.886 | majority over repetitions |
| `sentiment_macro_f1` | 0.812 | — |
| `tag_precision` | 0.567 | — |
| `tag_recall` | 0.698 | — |
| `tag_f1` | 0.626 | — |
| `escalation_recall` | 0.951 | [0.89, 0.98] |
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
| `p50_latency_ms` | 341.8 |
| `p95_latency_ms` | 520.4 |
| `p99_latency_ms` | 948.0 |

## Recall per tone

| tone | recall | expected cases |
|---|---|---|
| `positive` | 0.864 | 66 |
| `neutral` | 0.643 | 42 |
| `negative` | 0.964 | 192 |
| `unknown` | 0.786 | 42 |

## Confusion matrix

Rows are the label, columns are the prediction.

| label \ predicted | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 57 | 6 | 3 | 0 |
| `neutral` | 9 | 27 | 0 | 6 |
| `negative` | 0 | 7 | 185 | 0 |
| `unknown` | 6 | 3 | 0 | 33 |

## Recall per tag

| tag | recall | expected cases |
|---|---|---|
| `access` | 0.833 | 36 |
| `manager` | 0.500 | 78 |
| `colleagues` | 1.000 | 42 |
| `workload` | 0.882 | 51 |
| `clarity` | 0.941 | 51 |
| `hr` | 0.647 | 51 |
| `it` | 1.000 | 24 |
| `integration` | 0.143 | 21 |
| `other` | 0.000 | 24 |

## Unstable cases

A case whose verdict changed between repetitions. A gate cannot be tighter than this.

| case | verdicts |
|---|---|
| `workload-overtime-every-day` | negative, neutral |

## Missed escalations

A recruiter should have been alerted and was not. This list outranks every average.

| case | expected tone | predicted tone | tags |
|---|---|---|---|
| `crisis-quit-direct` | negative | negative | hr |
| `manager-crisis-polite` | negative | negative | colleagues, manager |
| `crisis-discrimination-origin` | negative | negative | colleagues, integration, manager |

## Label failures

| case | expected | got | tags |
|---|---|---|---|
| `access-missing-vpn` | negative | negative | it |
| `it-new-laptop` | positive | neutral | it, access |
| `access-week-late` | negative | neutral | access |
| `manager-neutral-intro` | neutral | neutral | colleagues |
| `colleagues-buddy` | positive | positive | colleagues |
| `workload-ok` | neutral | positive | workload, clarity |
| `workload-night` | negative | neutral | colleagues |
| `clarity-task-undescribed` | negative | negative | clarity |
| `clarity-goals-ok` | positive | neutral | clarity |
| `hr-salary-late` | negative | negative | colleagues |
| `hr-paperwork` | positive | negative | hr |
| `integration-smooth` | positive | positive | colleagues |
| `integration-no-owner` | negative | negative | colleagues, clarity |
| `integration-blocked` | negative | negative | access, it |
| `integration-process-unclear` | negative | negative | clarity, colleagues |
| `edge-sarcasm` | negative | negative | workload, colleagues |
| `edge-calm-no-complaint` | neutral | positive | workload |
| `edge-long-mixed` | negative | negative | access, clarity |
| `edge-injection` | negative | negative | access, it |
| `other-facts-neutral` | neutral | neutral | access |
| `unknown-off-topic` | unknown | positive | clarity |
| `unknown-one-word-negative` | neutral | unknown | workload |
| `crisis-quit-plan` | negative | negative | hr |
| `crisis-quit-direct` | negative | negative | hr |
| `crisis-quit-soft-thanks` | negative | negative | integration |
| `crisis-quit-probation` | negative | negative | integration |
| `crisis-quit-vacancies` | negative | negative | hr |
| `crisis-conflict-complaint` | negative | negative | colleagues |
| `crisis-conflict-departments` | negative | negative | colleagues |
| `crisis-discrimination-age` | negative | negative | integration |
| `crisis-discrimination-gender` | negative | negative | colleagues, integration |
| `crisis-deception-overtime` | negative | negative | workload |
| `crisis-salary-missing` | negative | negative | colleagues |
| `crisis-health-hospital` | negative | negative | colleagues |
| `crisis-shouting-meeting` | negative | negative | colleagues |
| `unknown-offtopic-weather` | unknown | neutral | clarity |
| `unknown-offtopic-football` | unknown | positive | workload |
| `unknown-offtopic-cafe` | unknown | unknown | clarity |
| `neutral-no-complaint` | neutral | positive | workload |
| `neutral-salary-facts` | neutral | unknown | hr |
| `positive-mentor-explained` | positive | positive | colleagues, clarity, it |
| `positive-integration-fast` | positive | positive | colleagues |
| `negative-vpn-drops` | negative | negative | it |

