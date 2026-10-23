# Sentiment eval — keyword

- command: `python -m onboarding.evals.sentiment --provider keyword --split test --repeat 1`
- commit: `eb70b76`
- environment: `local`
- split: `test`
- cases: 58 (dev 58, test 0)
- repetitions per case: 1
- calls: 58

## Quality

| metric | value | 95% CI |
|---|---|---|
| `sentiment_accuracy` | 0.345 | [0.24, 0.47] |
| `case_accuracy` | 0.345 | majority over repetitions |
| `sentiment_macro_f1` | 0.297 | — |
| `tag_precision` | 0.827 | — |
| `tag_recall` | 0.597 | — |
| `tag_f1` | 0.694 | — |
| `escalation_recall` | 0.600 | [0.31, 0.83] |
| `false_alarm_rate` | 0.188 | — |
| `fallback_rate` | 0.000 | — |
| `format_error_rate` | 0.000 | — |

## Latency

| metric | value |
|---|---|
| `p50_latency_ms` | 0.0 |
| `p95_latency_ms` | 0.0 |
| `p99_latency_ms` | 0.0 |

## Recall per tone

| tone | recall | expected cases |
|---|---|---|
| `positive` | 0.125 | 16 |
| `neutral` | 0.250 | 8 |
| `negative` | 0.438 | 32 |
| `unknown` | 1.000 | 2 |

## Confusion matrix

Rows are the label, columns are the prediction.

| label \ predicted | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 2 | 11 | 1 | 2 |
| `neutral` | 1 | 2 | 0 | 5 |
| `negative` | 0 | 14 | 14 | 4 |
| `unknown` | 0 | 0 | 0 | 2 |

## Recall per tag

| tag | recall | expected cases |
|---|---|---|
| `access` | 0.875 | 8 |
| `manager` | 0.692 | 13 |
| `colleagues` | 0.857 | 7 |
| `workload` | 0.300 | 10 |
| `clarity` | 0.500 | 12 |
| `hr` | 0.875 | 8 |
| `it` | 0.600 | 5 |
| `integration` | 0.400 | 5 |
| `other` | 0.000 | 4 |

Note: Set v2 (107 cases, dev/test split) replaces the 16-case v1 set; these numbers are not comparable with the 2026-10-23 v1 rows. Labels were written by one annotator: there is no inter-annotator kappa yet. Label rules: docs/evals/sentiment-guide.md.

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

