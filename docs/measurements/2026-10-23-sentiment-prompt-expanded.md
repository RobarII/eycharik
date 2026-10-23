# Sentiment eval — prompt

- command: `python -m onboarding.evals.sentiment --provider prompt --split test --repeat 3`
- commit: `460d91f`
- environment: `local`
- split: `test`
- model: `opencode-deepseek-v4.1-flash`
- rubric: `—`
- cases: 114 (dev 0, test 114)
- repetitions per case: 3
- calls: 342

## Quality

| metric | value | 95% CI |
|---|---|---|
| `sentiment_accuracy` | 0.848 | [0.81, 0.88] |
| `case_accuracy` | 0.904 | majority over repetitions |
| `sentiment_macro_f1` | 0.773 | — |
| `tag_precision` | 0.646 | — |
| `tag_recall` | 0.743 | — |
| `tag_f1` | 0.691 | — |
| `escalation_recall` | 0.873 | [0.79, 0.92] |
| `false_alarm_rate` | 0.371 | — |
| `fallback_rate` | 0.170 | — |
| `format_error_rate` | 0.000 | — |

## Cost

| metric | value |
|---|---|
| `cost_rub_total` | 0.0000 |
| `cost_rub_per_1k_calls` | 0.0000 |
| `input_tokens_total` | 0 |
| `cost_usd_total` | 0.000000 |
| `cost_usd_per_1k_calls` | 0.000000 |
| `priced_calls` | 0 / 342 |

## Latency

| metric | value |
|---|---|
| `p50_latency_ms` | 1367.2 |
| `p95_latency_ms` | 3077.8 |
| `p99_latency_ms` | 5593.4 |

## Recall per tone

| tone | recall | expected cases |
|---|---|---|
| `positive` | 0.864 | 66 |
| `neutral` | 0.690 | 42 |
| `negative` | 0.917 | 192 |
| `unknown` | 0.667 | 42 |

## Confusion matrix

Rows are the label, columns are the prediction.

| label \ predicted | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 57 | 9 | 0 | 0 |
| `neutral` | 9 | 29 | 0 | 4 |
| `negative` | 1 | 10 | 176 | 5 |
| `unknown` | 5 | 5 | 4 | 28 |

## Recall per tag

| tag | recall | expected cases |
|---|---|---|
| `access` | 0.889 | 36 |
| `manager` | 0.718 | 78 |
| `colleagues` | 0.881 | 42 |
| `workload` | 0.784 | 51 |
| `clarity` | 0.725 | 51 |
| `hr` | 0.706 | 51 |
| `it` | 0.667 | 24 |
| `integration` | 0.571 | 21 |
| `other` | 0.625 | 24 |

## Unstable cases

A case whose verdict changed between repetitions. A gate cannot be tighter than this.

| case | verdicts |
|---|---|
| `access-fixed-fast` | neutral, positive |
| `access-week-late` | negative, neutral |
| `crisis-deception-contract` | negative, neutral |
| `crisis-discrimination-age` | negative, unknown |
| `crisis-harassment-touch` | negative, neutral |
| `crisis-humiliation-chat` | negative, neutral |
| `crisis-humiliation-joke` | negative, neutral |
| `crisis-quit-probation` | negative, unknown |
| `crisis-quit-soft-thanks` | negative, positive |
| `edge-calm-no-complaint` | neutral, positive |
| `it-new-laptop` | neutral, positive |
| `manager-crisis-polite` | negative, neutral |
| `manager-micromanage` | negative, neutral |
| `manager-neutral-intro` | neutral, positive |
| `manager-support` | neutral, positive |
| `negative-docs-missing` | negative, neutral |
| `neutral-meeting-question` | neutral, unknown |
| `positive-integration-fast` | neutral, positive |
| `positive-team-lunch` | neutral, positive |
| `unknown-dots` | negative, neutral |
| `unknown-gibberish-2` | positive, unknown |
| `unknown-name` | positive, unknown |
| `unknown-neutral-emoji` | negative, unknown |
| `unknown-number` | neutral, unknown |
| `unknown-off-topic` | neutral, positive |
| `unknown-offtopic-cafe` | neutral, unknown |
| `unknown-offtopic-football` | neutral, positive, unknown |
| `workload-manageable` | neutral, positive |

## Missed escalations

A recruiter should have been alerted and was not. This list outranks every average.

| case | expected tone | predicted tone | tags |
|---|---|---|---|
| `workload-crisis-cant` | negative | unknown |  |
| `crisis-humiliation-chat` | negative | neutral | manager |
| `crisis-humiliation-joke` | negative | neutral | manager |
| `crisis-harassment-touch` | negative | neutral | colleagues |
| `crisis-discrimination-age` | negative | unknown |  |
| `crisis-deception-contract` | negative | neutral | hr |
| `manager-crisis-polite` | negative | neutral | manager |
| `crisis-quit-soft-thanks` | negative | positive | access, manager |
| `crisis-quit-probation` | negative | unknown |  |

## Label failures

| case | expected | got | tags |
|---|---|---|---|
| `access-missing-vpn` | negative | negative |  |
| `it-printer-neutral` | neutral | neutral | other |
| `manager-explains` | positive | positive | manager |
| `manager-neutral-intro` | neutral | positive | manager, integration |
| `colleagues-buddy` | positive | positive | colleagues, integration |
| `workload-ok` | neutral | positive | workload, clarity |
| `workload-crisis-cant` | negative | unknown |  |
| `hr-salary-late` | negative | negative | other |
| `hr-paperwork` | positive | neutral | hr |
| `hr-medical` | neutral | positive | integration |
| `hr-neutral-schedule` | neutral | neutral | other |
| `integration-no-owner` | negative | negative | integration |
| `integration-blocked` | negative | negative | access |
| `integration-process-unclear` | negative | negative | clarity, other |
| `edge-sarcasm` | negative | negative | workload |
| `edge-calm-no-complaint` | neutral | neutral | other |
| `edge-injection` | negative | negative | access, it |
| `other-facts-neutral` | neutral | neutral | integration |
| `unknown-off-topic` | unknown | positive | other |
| `unknown-one-word-negative` | neutral | unknown |  |
| `crisis-quit-plan` | negative | negative | integration |
| `crisis-quit-direct` | negative | negative | other |
| `crisis-quit-soft-thanks` | negative | negative | other |
| `crisis-quit-probation` | negative | negative | other |
| `crisis-quit-vacancies` | negative | negative | other |
| `crisis-conflict-departments` | negative | negative | colleagues |
| `crisis-humiliation-chat` | negative | neutral | manager |
| `crisis-humiliation-joke` | negative | neutral | manager |
| `crisis-harassment-messages` | negative | negative | other |
| `crisis-discrimination-age` | negative | unknown |  |
| `crisis-discrimination-gender` | negative | negative | manager, workload |
| `crisis-deception-overtime` | negative | negative | other |
| `crisis-salary-half` | negative | negative | other |
| `unknown-dots` | unknown | negative | access, it |
| `unknown-neutral-emoji` | unknown | unknown | other |
| `neutral-plan-facts` | neutral | neutral | manager |
| `positive-mentor-explained` | positive | positive | integration, colleagues |
| `positive-integration-fast` | positive | positive | colleagues |
| `negative-vpn-drops` | negative | negative | it |
| `it-new-laptop` | positive | positive | access |
| `clarity-checklist` | positive | positive |  |
| `edge-long-mixed` | negative | negative | access, workload, clarity |
| `crisis-shouting-meeting` | negative | negative | manager |
| `unknown-offtopic-weather` | unknown | unknown |  |
| `negative-printer` | negative | negative | access |
| `access-fixed-fast` | positive | positive | access, integration |
| `workload-burnout-soft` | negative | negative | other |
| `crisis-health-mental` | negative | negative |  |
| `negative-priorities-many` | negative | negative | clarity |

