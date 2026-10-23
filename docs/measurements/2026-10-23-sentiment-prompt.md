# Sentiment eval — prompt

- command: `python -m onboarding.evals.sentiment --provider prompt --split test --repeat 1`
- commit: `c0585bc`
- environment: `local`
- split: `test`
- model: `opencode-deepseek-v4.1-flash`
- rubric: `—`
- cases: 58 (dev 0, test 58)
- repetitions per case: 1
- calls: 58

## Quality

| metric | value | 95% CI |
|---|---|---|
| `sentiment_accuracy` | 0.741 | [0.62, 0.84] |
| `case_accuracy` | 0.741 | majority over repetitions |
| `sentiment_macro_f1` | 0.577 | — |
| `tag_precision` | 0.750 | — |
| `tag_recall` | 0.792 | — |
| `tag_f1` | 0.770 | — |
| `escalation_recall` | 0.700 | [0.40, 0.89] |
| `false_alarm_rate` | 0.375 | — |
| `fallback_rate` | 0.224 | — |
| `format_error_rate` | 0.000 | — |

## Cost

| metric | value |
|---|---|
| `cost_rub_total` | 0.0000 |
| `cost_rub_per_1k_calls` | 0.0000 |
| `input_tokens_total` | 0 |
| `cost_usd_total` | 0.000000 |
| `cost_usd_per_1k_calls` | 0.000000 |
| `priced_calls` | 0 / 58 |

## Latency

| metric | value |
|---|---|
| `p50_latency_ms` | 1366.4 |
| `p95_latency_ms` | 4701.1 |
| `p99_latency_ms` | 5637.5 |

## Recall per tone

| tone | recall | expected cases |
|---|---|---|
| `positive` | 0.875 | 16 |
| `neutral` | 0.375 | 8 |
| `negative` | 0.781 | 32 |
| `unknown` | 0.500 | 2 |

## Confusion matrix

Rows are the label, columns are the prediction.

| label \ predicted | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 14 | 1 | 1 | 0 |
| `neutral` | 2 | 3 | 0 | 3 |
| `negative` | 1 | 3 | 25 | 3 |
| `unknown` | 1 | 0 | 0 | 1 |

## Recall per tag

| tag | recall | expected cases |
|---|---|---|
| `access` | 1.000 | 8 |
| `manager` | 0.769 | 13 |
| `colleagues` | 1.000 | 7 |
| `workload` | 0.700 | 10 |
| `clarity` | 0.750 | 12 |
| `hr` | 0.875 | 8 |
| `it` | 0.800 | 5 |
| `integration` | 0.800 | 5 |
| `other` | 0.250 | 4 |

## Missed escalations

A recruiter should have been alerted and was not. This list outranks every average.

| case | expected tone | predicted tone | tags |
|---|---|---|---|
| `manager-crisis-bullying` | negative | negative | manager |
| `workload-crisis-cant` | negative | unknown |  |
| `crisis-quit-plan` | negative | unknown |  |

## Label failures

| case | expected | got | tags |
|---|---|---|---|
| `it-printer-neutral` | neutral | unknown |  |
| `access-week-late` | negative | neutral | access, hr |
| `manager-explains` | positive | positive | manager, integration |
| `manager-neutral-intro` | neutral | positive | manager, integration |
| `colleagues-clique` | negative | neutral | colleagues |
| `colleagues-buddy` | positive | negative | colleagues, clarity |
| `workload-ok` | neutral | positive | workload, clarity |
| `workload-crisis-cant` | negative | unknown |  |
| `workload-tasks-many` | negative | negative | clarity |
| `clarity-unclear-expectations` | negative | unknown |  |
| `clarity-task-undescribed` | negative | negative | clarity |
| `hr-medical` | neutral | neutral | integration |
| `integration-no-owner` | negative | negative | integration |
| `integration-blocked` | negative | negative | access, it |
| `edge-sarcasm` | negative | neutral | clarity |
| `edge-injection` | negative | positive | access |
| `other-facts-neutral` | neutral | unknown |  |
| `edge-thanks` | positive | neutral | hr |
| `unknown-off-topic` | unknown | positive | other |
| `unknown-one-word-negative` | neutral | unknown |  |
| `crisis-quit-plan` | negative | unknown |  |

