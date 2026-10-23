# Sentiment eval — keyword

- command: `python -m onboarding.evals.sentiment --provider keyword --split test --repeat 3`
- commit: `c0585bc`
- environment: `local`
- split: `test`
- model: `deterministic`
- rubric: `—`
- cases: 58 (dev 0, test 58)
- repetitions per case: 3
- calls: 174

## Quality

| metric | value | 95% CI |
|---|---|---|
| `sentiment_accuracy` | 0.345 | [0.28, 0.42] |
| `case_accuracy` | 0.345 | majority over repetitions |
| `sentiment_macro_f1` | 0.297 | — |
| `tag_precision` | 0.827 | — |
| `tag_recall` | 0.597 | — |
| `tag_f1` | 0.694 | — |
| `escalation_recall` | 0.600 | [0.42, 0.75] |
| `false_alarm_rate` | 0.188 | — |
| `fallback_rate` | 0.000 | — |
| `format_error_rate` | 0.000 | — |

## Cost

| metric | value |
|---|---|
| `cost_rub_total` | 0.0000 |
| `cost_rub_per_1k_calls` | 0.0000 |
| `input_tokens_total` | 0 |
| `cost_usd_total` | 0.000000 |
| `cost_usd_per_1k_calls` | 0.000000 |
| `priced_calls` | 0 / 174 |

## Latency

| metric | value |
|---|---|
| `p50_latency_ms` | 0.0 |
| `p95_latency_ms` | 0.0 |
| `p99_latency_ms` | 0.0 |

## Recall per tone

| tone | recall | expected cases |
|---|---|---|
| `positive` | 0.125 | 48 |
| `neutral` | 0.250 | 24 |
| `negative` | 0.438 | 96 |
| `unknown` | 1.000 | 6 |

## Confusion matrix

Rows are the label, columns are the prediction.

| label \ predicted | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 6 | 33 | 3 | 6 |
| `neutral` | 3 | 6 | 0 | 15 |
| `negative` | 0 | 42 | 42 | 12 |
| `unknown` | 0 | 0 | 0 | 6 |

## Recall per tag

| tag | recall | expected cases |
|---|---|---|
| `access` | 0.875 | 24 |
| `manager` | 0.692 | 39 |
| `colleagues` | 0.857 | 21 |
| `workload` | 0.300 | 30 |
| `clarity` | 0.500 | 36 |
| `hr` | 0.875 | 24 |
| `it` | 0.600 | 15 |
| `integration` | 0.400 | 15 |
| `other` | 0.000 | 12 |

## Missed escalations

A recruiter should have been alerted and was not. This list outranks every average.

| case | expected tone | predicted tone | tags |
|---|---|---|---|
| `manager-crisis-polite` | negative | neutral | manager |
| `workload-crisis-cant` | negative | unknown |  |
| `hr-crisis-discrimination` | negative | neutral | hr |
| `crisis-quit-plan` | negative | unknown |  |

## Label failures

| case | expected | got | tags |
|---|---|---|---|
| `access-missing-vpn` | negative | negative |  |
| `access-fixed-fast` | positive | neutral | access, it |
| `access-badge-wait` | negative | neutral | access |
| `it-new-laptop` | positive | neutral | it |
| `it-printer-neutral` | neutral | unknown |  |
| `access-week-late` | negative | neutral | access, hr |
| `manager-support` | positive | neutral | manager |
| `manager-micromanage` | negative | neutral | manager |
| `manager-public-praise` | positive | neutral | manager, clarity |
| `manager-explains` | positive | neutral | manager |
| `manager-crisis-polite` | negative | neutral | manager |
| `colleagues-warm` | positive | positive | colleagues |
| `colleagues-no-help` | negative | neutral | colleagues |
| `colleagues-clique` | negative | neutral | colleagues |
| `colleagues-buddy` | positive | negative | colleagues, clarity |
| `colleagues-offsite` | positive | neutral | colleagues |
| `workload-ok` | neutral | positive | clarity |
| `workload-overtime-every-day` | negative | neutral | workload |
| `workload-manageable` | positive | neutral | workload, hr |
| `workload-crisis-cant` | negative | unknown |  |
| `workload-tasks-many` | negative | negative | clarity |
| `workload-night` | negative | neutral | colleagues |
| `clarity-good` | positive | neutral | clarity |
| `clarity-unclear-expectations` | negative | unknown |  |
| `clarity-checklist` | positive | positive |  |
| `clarity-task-undescribed` | negative | neutral | clarity |
| `clarity-priority-chaos` | negative | negative | clarity |
| `clarity-goals-ok` | positive | unknown |  |
| `hr-delay-contract` | negative | neutral | hr |
| `hr-paperwork` | positive | neutral | hr |
| `hr-medical` | neutral | unknown |  |
| `hr-crisis-discrimination` | negative | neutral | hr |
| `integration-smooth` | positive | neutral | integration |
| `integration-no-owner` | negative | unknown |  |
| `integration-blocked` | negative | neutral | access, integration |
| `integration-process-unclear` | negative | negative |  |
| `edge-sarcasm` | negative | neutral | clarity |
| `edge-calm-no-complaint` | neutral | unknown |  |
| `edge-long-mixed` | negative | neutral | access, clarity, hr |
| `edge-injection` | negative | negative | access, clarity |
| `other-facts-neutral` | neutral | unknown |  |
| `edge-english` | positive | unknown |  |
| `edge-thanks` | positive | neutral | hr |
| `unknown-off-topic` | unknown | unknown |  |
| `unknown-one-word-negative` | neutral | unknown |  |
| `crisis-quit-plan` | negative | unknown |  |

