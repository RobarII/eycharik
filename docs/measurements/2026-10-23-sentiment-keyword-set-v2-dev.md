# Sentiment eval — keyword

- command: `python -m onboarding.evals.sentiment --provider keyword --split dev --repeat 1`
- commit: `eb70b76`
- environment: `local`
- split: `dev`
- cases: 49 (dev 49, test 0)
- repetitions per case: 1
- calls: 49

## Quality

| metric | value | 95% CI |
|---|---|---|
| `sentiment_accuracy` | 0.429 | [0.30, 0.57] |
| `case_accuracy` | 0.429 | majority over repetitions |
| `sentiment_macro_f1` | 0.390 | — |
| `tag_precision` | 0.735 | — |
| `tag_recall` | 0.600 | — |
| `tag_f1` | 0.661 | — |
| `escalation_recall` | 0.400 | [0.12, 0.77] |
| `false_alarm_rate` | 0.136 | — |
| `fallback_rate` | 0.000 | — |
| `format_error_rate` | 0.000 | — |

## Latency

| metric | value |
|---|---|
| `p50_latency_ms` | 0.0 |
| `p95_latency_ms` | 0.0 |
| `p99_latency_ms` | 0.2 |

## Recall per tone

| tone | recall | expected cases |
|---|---|---|
| `positive` | 0.125 | 8 |
| `neutral` | 0.818 | 11 |
| `negative` | 0.296 | 27 |
| `unknown` | 1.000 | 3 |

## Confusion matrix

Rows are the label, columns are the prediction.

| label \ predicted | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 1 | 4 | 0 | 3 |
| `neutral` | 1 | 9 | 0 | 1 |
| `negative` | 2 | 14 | 8 | 3 |
| `unknown` | 0 | 0 | 0 | 3 |

## Recall per tag

| tag | recall | expected cases |
|---|---|---|
| `access` | 0.800 | 5 |
| `manager` | 0.625 | 8 |
| `colleagues` | 0.889 | 9 |
| `workload` | 0.375 | 8 |
| `clarity` | 0.636 | 11 |
| `hr` | 0.500 | 6 |
| `it` | 0.800 | 5 |
| `integration` | 0.333 | 6 |
| `other` | 0.000 | 2 |

Note: Set v2 (107 cases, dev/test split) replaces the 16-case v1 set; these numbers are not comparable with the 2026-10-23 v1 rows. Labels were written by one annotator: there is no inter-annotator kappa yet. Label rules: docs/evals/sentiment-guide.md.

## Missed escalations

A recruiter should have been alerted and was not. This list outranks every average.

| case | expected tone | predicted tone | tags |
|---|---|---|---|
| `manager-crisis-humiliation` | negative | neutral | manager, colleagues |
| `colleagues-crisis-harassment` | negative | neutral | colleagues |
| `crisis-quit-polite` | negative | unknown |  |

## Label failures

| case | expected | got | tags |
|---|---|---|---|
| `access-missing-1c` | negative | neutral | access, it |
| `access-partial` | negative | neutral | access, it |
| `it-old-laptop` | negative | neutral | it |
| `it-helpful` | positive | neutral | it |
| `access-double-auth` | negative | positive |  |
| `manager-no-feedback` | negative | neutral | manager, clarity |
| `manager-no-one-on-one` | negative | negative |  |
| `manager-deadline-pressure` | negative | neutral | manager, clarity |
| `manager-changes-tasks` | negative | neutral | clarity |
| `manager-crisis-humiliation` | negative | neutral | manager, colleagues |
| `colleagues-cold` | negative | neutral | it, colleagues |
| `colleagues-lunch` | positive | neutral | colleagues |
| `colleagues-chat-silent` | negative | unknown |  |
| `colleagues-crisis-harassment` | negative | neutral | colleagues |
| `colleagues-other-language` | negative | neutral | colleagues |
| `workload-bored` | negative | neutral | it, clarity |
| `workload-week-one` | neutral | neutral | clarity |
| `workload-flex` | positive | unknown |  |
| `clarity-docs-missing` | negative | neutral | hr |
| `clarity-training` | positive | unknown |  |
| `hr-documents` | positive | neutral | hr |
| `hr-bonus-unclear` | negative | negative | clarity |
| `hr-contract-ok` | positive | neutral | it |
| `hr-no-response` | negative | neutral | hr |
| `integration-other-dept` | negative | neutral | integration |
| `integration-meetings` | neutral | unknown |  |
| `integration-handoff` | positive | unknown |  |
| `integration-neutral-lists` | neutral | positive | integration |
| `edge-negation` | negative | negative |  |
| `edge-mixed` | negative | positive | manager, colleagues |
| `other-personal` | neutral | neutral | manager |
| `edge-short-negative` | negative | unknown |  |
| `crisis-quit-polite` | negative | unknown |  |

