# Sentiment eval — prompt

- command: `python -m onboarding.evals.sentiment --provider keyword --split test --repeat 1 --compare docs/measurements/2026-10-23-sentiment-keyword-set-v2-test.jsonl`
- commit: `eb70b76`
- environment: `local`
- split: `test`
- cases: 58 (dev 58, test 0)
- repetitions per case: 3
- calls: 174

## Quality

| metric | value | 95% CI |
|---|---|---|
| `sentiment_accuracy` | 0.770 | [0.70, 0.83] |
| `case_accuracy` | 0.793 | majority over repetitions |
| `sentiment_macro_f1` | 0.606 | — |
| `tag_precision` | 0.740 | — |
| `tag_recall` | 0.829 | — |
| `tag_f1` | 0.782 | — |
| `escalation_recall` | 0.800 | [0.63, 0.90] |
| `false_alarm_rate` | 0.403 | — |
| `fallback_rate` | 0.195 | — |
| `format_error_rate` | 0.000 | — |

## Latency

| metric | value |
|---|---|
| `p50_latency_ms` | 1354.6 |
| `p95_latency_ms` | 2673.7 |
| `p99_latency_ms` | 3994.4 |

## Recall per tone

| tone | recall | expected cases |
|---|---|---|
| `positive` | 0.771 | 48 |
| `neutral` | 0.500 | 24 |
| `negative` | 0.854 | 96 |
| `unknown` | 0.500 | 6 |

## Confusion matrix

Rows are the label, columns are the prediction.

| label \ predicted | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 37 | 10 | 0 | 1 |
| `neutral` | 7 | 12 | 0 | 5 |
| `negative` | 0 | 6 | 82 | 8 |
| `unknown` | 2 | 0 | 1 | 3 |

## Recall per tag

| tag | recall | expected cases |
|---|---|---|
| `access` | 1.000 | 24 |
| `manager` | 0.821 | 39 |
| `colleagues` | 0.857 | 21 |
| `workload` | 0.800 | 30 |
| `clarity` | 0.833 | 36 |
| `hr` | 0.792 | 24 |
| `it` | 0.867 | 15 |
| `integration` | 0.800 | 15 |
| `other` | 0.583 | 12 |

Note: Set v2 (107 cases, dev/test split) replaces the 16-case v1 set; these numbers are not comparable with the 2026-10-23 v1 rows. Labels were written by one annotator: there is no inter-annotator kappa yet. Label rules: docs/evals/sentiment-guide.md.

## Comparison

- metric: `case_accuracy`
- paired cases: 58
- baseline: 0.345
- candidate: 0.776
- delta: +0.431 (95% bootstrap CI [0.29, 0.57])
- p(delta <= 0): 0.000
- reading: candidate is better

## Unstable cases

A case whose verdict changed between repetitions. A gate cannot be tighter than this.

| case | verdicts |
|---|---|
| `clarity-unclear-expectations` | negative, unknown |
| `colleagues-clique` | negative, neutral, unknown |
| `colleagues-no-help` | negative, neutral |
| `colleagues-offsite` | neutral, positive |
| `crisis-quit-plan` | negative, unknown |
| `edge-calm-no-complaint` | neutral, positive, unknown |
| `edge-english` | positive, unknown |
| `edge-injection` | negative, unknown |
| `edge-sarcasm` | negative, neutral |
| `edge-thanks` | neutral, positive |
| `hr-crisis-discrimination` | negative, neutral |
| `hr-medical` | positive, unknown |
| `hr-paperwork` | neutral, positive |
| `integration-blocked` | negative, neutral |
| `integration-smooth` | neutral, positive |
| `it-new-laptop` | neutral, positive |
| `it-printer-neutral` | neutral, unknown |
| `manager-neutral-intro` | neutral, positive |
| `manager-public-praise` | neutral, positive |
| `manager-support` | neutral, positive |
| `unknown-empty` | negative, unknown |
| `unknown-off-topic` | positive, unknown |
| `unknown-one-word-negative` | neutral, unknown |
| `workload-ok` | neutral, positive |

## Missed escalations

A recruiter should have been alerted and was not. This list outranks every average.

| case | expected tone | predicted tone | tags |
|---|---|---|---|
| `workload-crisis-cant` | negative | unknown |  |
| `hr-crisis-discrimination` | negative | neutral | hr |
| `crisis-quit-plan` | negative | unknown |  |

## Label failures

| case | expected | got | tags |
|---|---|---|---|
| `manager-explains` | positive | positive | manager, integration |
| `manager-neutral-intro` | neutral | positive | manager, integration |
| `colleagues-buddy` | positive | positive | colleagues, integration |
| `colleagues-offsite` | positive | neutral | colleagues |
| `workload-ok` | neutral | positive | workload, clarity |
| `workload-crisis-cant` | negative | unknown |  |
| `hr-medical` | neutral | positive | integration |
| `hr-neutral-schedule` | neutral | neutral | other |
| `integration-smooth` | positive | neutral | integration, other |
| `integration-process-unclear` | negative | negative | clarity, other |
| `edge-sarcasm` | negative | negative | workload |
| `edge-calm-no-complaint` | neutral | positive | workload |
| `edge-injection` | negative | negative | access |
| `edge-thanks` | positive | neutral | hr |
| `unknown-off-topic` | unknown | positive | other |
| `unknown-one-word-negative` | neutral | unknown | other |
| `crisis-quit-plan` | negative | negative | other |
| `it-printer-neutral` | neutral | neutral | other |
| `colleagues-clique` | negative | unknown | other |
| `clarity-unclear-expectations` | negative | unknown |  |
| `integration-blocked` | negative | negative | access, it |
| `other-facts-neutral` | neutral | neutral | integration |
| `edge-english` | positive | unknown |  |
| `clarity-task-undescribed` | negative | negative | clarity |

