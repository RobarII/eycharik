---
title: "Оценка риска: decisions, test"
summary: "114 кейсов, sentiment_accuracy 0.684, tag_f1 0.539, гейты провалены; команда и коммит в шапке."
kind: "измерение"
owner: "p4ulbr4dl3y"
status: "принято"
last_verified: "2026-10-25"
---

# Оценка риска — decisions

- команда: `python -m onboarding.evals.sentiment --provider decisions --split test --repeat 1`
- коммит: `f7006dd`
- окружение: `local`
- выборка: `test`
- модель: `frida-decisions`
- рубрика: `sentiment-jev@1`
- кейсов: 114 (dev 0, test 114)
- повторов на кейс: 1
- вызовов: 114

## Качество

| метрика | значение | 95% CI |
|---|---|---|
| `sentiment_accuracy` | 0.684 | [0.59, 0.76] |
| `case_accuracy` | 0.684 | majority over repetitions |
| `sentiment_macro_f1` | 0.586 | — |
| `tag_precision` | 0.446 | — |
| `tag_recall` | 0.683 | — |
| `tag_f1` | 0.539 | — |
| `escalation_recall` | 0.412 | [0.26, 0.58] |
| `false_alarm_rate` | 0.113 | — |
| `fallback_rate` | 0.000 | — |
| `format_error_rate` | 0.000 | — |

## Стоимость

| метрика | значение |
|---|---|
| `cost_rub_total` | 0.0000 |
| `cost_rub_per_1k_calls` | 0.0000 |
| `input_tokens_total` | 0 |
| `output_tokens_total` | 0 |
| `cost_usd_total` | 0.000000 |
| `cost_usd_per_1k_calls` | 0.000000 |
| `priced_calls` | 0 / 114 |

## Задержка

| метрика | значение |
|---|---|
| `p50_latency_ms` | 915.7 |
| `p95_latency_ms` | 932.6 |
| `p99_latency_ms` | 936.3 |

## Полнота по тону

| тон | полнота | кейсов с меткой |
|---|---|---|
| `positive` | 0.864 | 22 |
| `neutral` | 0.214 | 14 |
| `negative` | 0.688 | 64 |
| `unknown` | 0.857 | 14 |

## Матрица ошибок

Строки — метка, столбцы — предсказание.

| метка \ предсказание | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 19 | 0 | 0 | 3 |
| `neutral` | 7 | 3 | 0 | 4 |
| `negative` | 4 | 2 | 44 | 14 |
| `unknown` | 1 | 1 | 0 | 12 |

## Полнота по тегу

| тег | полнота | кейсов с меткой |
|---|---|---|
| `access` | 1.000 | 12 |
| `manager` | 0.462 | 26 |
| `colleagues` | 0.786 | 14 |
| `workload` | 0.882 | 17 |
| `clarity` | 0.765 | 17 |
| `hr` | 0.765 | 17 |
| `it` | 1.000 | 8 |
| `integration` | 0.286 | 7 |
| `other` | 0.000 | 8 |

## Пропущенные эскалации

Рекрутёра надо было предупредить, а его не предупредили. Этот список важнее
любого среднего.

| кейс | ожидаемый тон | предсказанный тон | теги |
|---|---|---|---|
| `manager-crisis-polite` | negative | positive | manager, colleagues |
| `hr-crisis-discrimination` | negative | unknown | hr |
| `crisis-quit-plan` | negative | unknown | hr |
| `crisis-abuse-soft` | negative | positive | manager, colleagues, hr |
| `crisis-quit-direct` | negative | negative | clarity, hr, workload |
| `crisis-quit-vacancies` | negative | unknown | hr |
| `crisis-conflict-open` | negative | negative | colleagues, manager |
| `crisis-humiliation-joke` | negative | positive | colleagues |
| `crisis-bullying-senior` | negative | negative | colleagues |
| `crisis-harassment-touch` | negative | negative | colleagues |
| `crisis-harassment-messages` | negative | negative | workload |
| `crisis-discrimination-age` | negative | negative | hr |
| `crisis-discrimination-gender` | negative | negative | hr |
| `crisis-discrimination-origin` | negative | unknown | colleagues |
| `crisis-deception-contract` | negative | negative | hr |
| `crisis-deception-overtime` | negative | negative | workload |
| `crisis-salary-missing` | negative | unknown | hr |
| `crisis-salary-half` | negative | negative | hr |
| `crisis-health-collapse` | negative | unknown | workload |
| `crisis-health-hospital` | negative | negative | workload |

## Ошибки разметки

| кейс | ожидалось | получено | теги |
|---|---|---|---|
| `it-printer-neutral` | neutral | unknown | it |
| `access-week-late` | negative | neutral | access, hr |
| `manager-micromanage` | negative | unknown | manager |
| `manager-explains` | positive | unknown | clarity, manager, colleagues |
| `manager-neutral-intro` | neutral | unknown | integration, colleagues, manager |
| `manager-crisis-polite` | negative | positive | manager, colleagues |
| `colleagues-buddy` | positive | unknown | colleagues |
| `workload-ok` | neutral | positive | clarity, workload |
| `workload-overtime-every-day` | negative | neutral | workload |
| `workload-night` | negative | unknown | hr, colleagues, clarity |
| `clarity-good` | positive | unknown | clarity |
| `clarity-unclear-expectations` | negative | unknown | integration |
| `clarity-task-undescribed` | negative | unknown | clarity |
| `hr-salary-late` | negative | negative | access |
| `hr-medical` | neutral | positive | clarity, hr |
| `hr-crisis-discrimination` | negative | unknown | hr |
| `hr-neutral-schedule` | neutral | unknown | hr, clarity, workload |
| `integration-no-owner` | negative | unknown | access |
| `integration-blocked` | negative | negative | access, it |
| `integration-process-unclear` | negative | negative | clarity |
| `edge-sarcasm` | negative | positive | workload, colleagues, clarity |
| `edge-calm-no-complaint` | neutral | positive | clarity |
| `edge-long-mixed` | negative | negative | access |
| `edge-injection` | negative | negative | access |
| `other-facts-neutral` | neutral | positive | access, workload, it |
| `unknown-off-topic` | unknown | positive | clarity |
| `unknown-one-word-negative` | neutral | positive | clarity, hr |
| `crisis-quit-plan` | negative | unknown | hr |
| `crisis-deception` | negative | negative | clarity |
| `crisis-abuse-soft` | negative | positive | manager, colleagues, hr |
| `crisis-quit-direct` | negative | negative | clarity, hr, workload |
| `crisis-quit-soft-thanks` | negative | negative | integration |
| `crisis-quit-probation` | negative | negative | workload |
| `crisis-quit-vacancies` | negative | unknown | hr |
| `crisis-conflict-complaint` | negative | negative | hr |
| `crisis-conflict-departments` | negative | negative | colleagues, hr, clarity |
| `crisis-humiliation-joke` | negative | positive | colleagues |
| `crisis-harassment-messages` | negative | negative | workload |
| `crisis-discrimination-age` | negative | negative | hr |
| `crisis-discrimination-gender` | negative | negative | hr |
| `crisis-discrimination-origin` | negative | unknown | colleagues |
| `crisis-deception-overtime` | negative | negative | workload |
| `crisis-salary-missing` | negative | unknown | hr |
| `crisis-health-collapse` | negative | unknown | workload |
| `crisis-shouting-meeting` | negative | negative | colleagues |
| `unknown-offtopic-weather` | unknown | neutral | clarity |
| `unknown-offtopic-football` | unknown | unknown | colleagues, clarity, workload |
| `unknown-offtopic-cafe` | unknown | unknown | clarity, integration, workload |
| `neutral-meeting-question` | neutral | unknown | hr |
| `neutral-plan-facts` | neutral | positive | clarity |
| `neutral-no-complaint` | neutral | positive | hr |
| `neutral-salary-facts` | neutral | neutral | clarity |
| `positive-mentor-explained` | positive | positive | clarity |
| `positive-integration-fast` | positive | positive | hr, clarity, colleagues |
| `negative-chat-silent` | negative | negative | access |
| `negative-priorities-many` | negative | unknown | clarity, workload |
| `negative-docs-missing` | negative | unknown | clarity |
| `negative-plan-absent` | negative | unknown | it |

