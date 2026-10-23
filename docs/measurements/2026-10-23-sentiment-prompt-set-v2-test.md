# Sentiment eval — prompt

- command: `python -m onboarding.evals.sentiment --provider prompt --split test --repeat 3 --min-interval 0.5 --compare docs/measurements/2026-10-23-sentiment-keyword-set-v2-test.jsonl`
- commit: `4f894c2`
- environment: `local`
- split: `test`
- cases: 58 (dev 0, test 58)
- repetitions per case: 3
- calls: 174

## Quality

| metric | value | 95% CI |
|---|---|---|
| `sentiment_accuracy` | 0.851 | [0.79, 0.90] |
| `sentiment_macro_f1` | 0.750 | — |
| `tag_precision` | 0.705 | — |
| `tag_recall` | 0.773 | — |
| `tag_f1` | 0.737 | — |
| `escalation_recall` | 0.867 | [0.70, 0.95] |
| `false_alarm_rate` | 0.403 | — |
| `fallback_rate` | 0.172 | — |
| `format_error_rate` | 0.000 | — |

## Latency

| metric | value |
|---|---|
| `p50_latency_ms` | 1349.7 |
| `p95_latency_ms` | 3030.8 |
| `p99_latency_ms` | 5484.2 |

## Recall per tone

| tone | recall | expected cases |
|---|---|---|
| `positive` | 0.938 | 48 |
| `neutral` | 0.542 | 24 |
| `negative` | 0.875 | 96 |
| `unknown` | 1.000 | 6 |

## Confusion matrix

Rows are the label, columns are the prediction.

| label \ predicted | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 45 | 2 | 0 | 1 |
| `neutral` | 9 | 13 | 0 | 2 |
| `negative` | 0 | 8 | 84 | 4 |
| `unknown` | 0 | 0 | 0 | 6 |

## Recall per tag

| tag | recall | expected cases |
|---|---|---|
| `access` | 0.917 | 24 |
| `manager` | 0.769 | 39 |
| `colleagues` | 1.000 | 21 |
| `workload` | 0.733 | 30 |
| `clarity` | 0.778 | 36 |
| `hr` | 0.750 | 24 |
| `it` | 0.733 | 15 |
| `integration` | 0.667 | 15 |
| `other` | 0.417 | 12 |

## Comparison

- metric: `sentiment_accuracy`
- paired cases: 58
- baseline: 0.345
- candidate: 0.914
- delta: +0.569 (95% bootstrap CI [0.43, 0.71])
- p(delta <= 0): 0.000
- reading: candidate is better

## Unstable cases

A case whose verdict changed between repetitions. A gate cannot be tighter than this.

| case | verdicts |
|---|---|
| `access-badge-wait` | negative, neutral |
| `access-week-late` | negative, neutral |
| `clarity-goals-ok` | positive, unknown |
| `clarity-task-undescribed` | negative, neutral |
| `colleagues-no-help` | negative, neutral |
| `crisis-quit-plan` | negative, unknown |
| `edge-calm-no-complaint` | neutral, positive |
| `edge-sarcasm` | negative, neutral |
| `hr-delay-contract` | negative, neutral |
| `hr-medical` | neutral, positive |
| `integration-blocked` | negative, neutral |
| `manager-explains` | neutral, positive |
| `manager-micromanage` | negative, neutral |
| `unknown-one-word-negative` | neutral, unknown |
| `workload-manageable` | neutral, positive |

## Missed escalations

A recruiter should have been alerted and was not. This list outranks every average.

| case | expected tone | predicted tone | tags |
|---|---|---|---|
| `workload-crisis-cant` | negative | unknown |  |
| `workload-crisis-cant` | negative | unknown |  |
| `crisis-quit-plan` | negative | unknown |  |
| `workload-crisis-cant` | negative | unknown |  |

## Label failures

| case | expected | got | tags |
|---|---|---|---|
| `it-printer-neutral` | neutral | neutral | other |
| `manager-micromanage` | negative | neutral | manager |
| `manager-explains` | positive | positive | manager, integration |
| `manager-neutral-intro` | neutral | positive | manager, integration, colleagues |
| `colleagues-no-help` | negative | neutral | colleagues |
| `colleagues-buddy` | positive | positive | colleagues |
| `workload-ok` | neutral | positive | workload, clarity |
| `workload-crisis-cant` | negative | unknown |  |
| `workload-burnout-soft` | negative | negative | other |
| `clarity-task-undescribed` | negative | negative | clarity |
| `hr-delay-contract` | negative | neutral | hr |
| `hr-medical` | neutral | positive | integration |
| `hr-neutral-schedule` | neutral | neutral | other |
| `integration-blocked` | negative | negative | access, workload |
| `integration-process-unclear` | negative | negative | clarity, other |
| `edge-sarcasm` | negative | neutral | clarity |
| `edge-calm-no-complaint` | neutral | neutral | other |
| `edge-injection` | negative | negative | access |
| `unknown-off-topic` | unknown | unknown |  |
| `unknown-one-word-negative` | neutral | neutral | integration |
| `crisis-quit-plan` | negative | negative | other |
| `access-missing-vpn` | negative | negative |  |
| `it-printer-neutral` | neutral | neutral | other |
| `access-week-late` | negative | neutral | access, hr |
| `manager-explains` | positive | neutral | manager |
| `manager-neutral-intro` | neutral | positive | manager |
| `colleagues-buddy` | positive | positive | colleagues, integration |
| `workload-ok` | neutral | positive | workload, clarity |
| `workload-manageable` | positive | neutral | workload, hr |
| `workload-crisis-cant` | negative | unknown |  |
| `clarity-task-undescribed` | negative | neutral | clarity |
| `hr-medical` | neutral | positive | integration |
| `hr-neutral-schedule` | neutral | neutral | other |
| `integration-blocked` | negative | negative | access, workload |
| `integration-process-unclear` | negative | negative |  |
| `edge-sarcasm` | negative | negative | workload |
| `edge-calm-no-complaint` | neutral | neutral | other |
| `edge-injection` | negative | negative | access, clarity |
| `unknown-one-word-negative` | neutral | unknown |  |
| `crisis-quit-plan` | negative | unknown |  |
| `access-missing-vpn` | negative | negative | it |
| `access-badge-wait` | negative | neutral | access |
| `it-printer-neutral` | neutral | neutral | other |
| `manager-explains` | positive | positive | manager |
| `manager-neutral-intro` | neutral | positive | manager, integration |
| `colleagues-buddy` | positive | positive | colleagues, integration |
| `workload-ok` | neutral | positive | workload, clarity |
| `workload-crisis-cant` | negative | unknown |  |
| `workload-tasks-many` | negative | negative | clarity |
| `clarity-goals-ok` | positive | unknown |  |
| `hr-salary-late` | negative | negative | other |
| `hr-medical` | neutral | neutral | integration |
| `integration-no-owner` | negative | negative | integration |
| `integration-blocked` | negative | neutral | access, integration |
| `integration-process-unclear` | negative | negative | clarity, other |
| `edge-sarcasm` | negative | negative | workload |
| `edge-calm-no-complaint` | neutral | positive | workload |
| `edge-long-mixed` | negative | negative | access, clarity, integration |
| `edge-injection` | negative | negative | access |
| `unknown-one-word-negative` | neutral | unknown |  |
| `crisis-quit-plan` | negative | negative | integration |

