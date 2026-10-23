# Sentiment eval — prompt

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
| `sentiment_accuracy` | 0.816 | [0.69, 0.90] |
| `case_accuracy` | 0.816 | majority over repetitions |
| `sentiment_macro_f1` | 0.743 | — |
| `tag_precision` | 0.623 | — |
| `tag_recall` | 0.717 | — |
| `tag_f1` | 0.667 | — |
| `escalation_recall` | 0.800 | [0.38, 0.96] |
| `false_alarm_rate` | 0.409 | — |
| `fallback_rate` | 0.245 | — |
| `format_error_rate` | 0.000 | — |

## Latency

| metric | value |
|---|---|
| `p50_latency_ms` | 1438.5 |
| `p95_latency_ms` | 5555.3 |
| `p99_latency_ms` | 7409.0 |

## Recall per tone

| tone | recall | expected cases |
|---|---|---|
| `positive` | 0.875 | 8 |
| `neutral` | 0.818 | 11 |
| `negative` | 0.815 | 27 |
| `unknown` | 0.667 | 3 |

## Confusion matrix

Rows are the label, columns are the prediction.

| label \ predicted | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 7 | 1 | 0 | 0 |
| `neutral` | 1 | 9 | 0 | 1 |
| `negative` | 0 | 3 | 22 | 2 |
| `unknown` | 1 | 0 | 0 | 2 |

## Recall per tag

| tag | recall | expected cases |
|---|---|---|
| `access` | 0.800 | 5 |
| `manager` | 0.750 | 8 |
| `colleagues` | 0.778 | 9 |
| `workload` | 0.750 | 8 |
| `clarity` | 0.727 | 11 |
| `hr` | 0.667 | 6 |
| `it` | 0.800 | 5 |
| `integration` | 0.500 | 6 |
| `other` | 0.500 | 2 |

Note: Set v2 (107 cases, dev/test split) replaces the 16-case v1 set; these numbers are not comparable with the 2026-10-23 v1 rows. Labels were written by one annotator: there is no inter-annotator kappa yet. Label rules: docs/evals/sentiment-guide.md.

## Missed escalations

A recruiter should have been alerted and was not. This list outranks every average.

| case | expected tone | predicted tone | tags |
|---|---|---|---|
| `manager-crisis-humiliation` | negative | neutral | manager, colleagues |

## Label failures

| case | expected | got | tags |
|---|---|---|---|
| `access-missing-1c` | negative | neutral | access, it |
| `access-double-auth` | negative | negative | it |
| `it-neutral-setup` | neutral | positive | access, integration |
| `manager-no-feedback` | negative | neutral | manager, clarity |
| `manager-changes-tasks` | negative | negative | clarity, workload |
| `manager-crisis-humiliation` | negative | neutral | manager, colleagues |
| `colleagues-chat-silent` | negative | unknown |  |
| `colleagues-meeting-neutral` | neutral | neutral | manager, clarity |
| `colleagues-other-language` | negative | negative | colleagues |
| `workload-bored` | negative | negative | workload |
| `workload-week-one` | neutral | neutral | clarity |
| `clarity-first-week-neutral` | neutral | neutral | access, integration |
| `hr-documents` | positive | neutral | hr |
| `hr-bonus-unclear` | negative | negative | clarity |
| `integration-other-dept` | negative | negative | colleagues, workload |
| `integration-meetings` | neutral | unknown |  |
| `edge-negation` | negative | negative |  |
| `other-personal` | neutral | neutral | manager, other |
| `edge-short-negative` | negative | unknown |  |
| `unknown-emoji` | unknown | positive | other |
| `crisis-quit-polite` | negative | negative | other |

