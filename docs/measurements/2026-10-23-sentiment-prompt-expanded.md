---
title: "Оценка 2026-10-23: риск-радар промпт расширенный набор"
summary: "114 кейсов, гейты пройдены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-23 — пройдена

- команда: `python -m onboarding.evals.sentiment --provider prompt --split test --repeat 3`
- коммит: `460d91f`
- окружение: `local`
- сплит: `test`
- модель: `opencode-deepseek-v4.1-flash`
- рубрика: `—`
- кейсов: 114 (dev 0, test 114)
- повторов на кейс: 3
- вызовов: 342

## Качество

| метрика | значение | 95% ДИ |
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

## Стоимость

| метрика | значение |
|---|---|
| `cost_rub_total` | 0.0000 |
| `cost_rub_per_1k_calls` | 0.0000 |
| `input_tokens_total` | 0 |
| `cost_usd_total` | 0.000000 |
| `cost_usd_per_1k_calls` | 0.000000 |
| `priced_calls` | 0 / 342 |

## Задержка

| метрика | значение |
|---|---|
| `p50_latency_ms` | 1367.2 |
| `p95_latency_ms` | 3077.8 |
| `p99_latency_ms` | 5593.4 |

## Полнота по тону

| тон | полнота | ожидаемых кейсов |
|---|---|---|
| `positive` | 0.864 | 66 |
| `neutral` | 0.690 | 42 |
| `negative` | 0.917 | 192 |
| `unknown` | 0.667 | 42 |

## Матрица ошибок

Строки — метка, столбцы — предсказание.

| метка \ предсказание | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 57 | 9 | 0 | 0 |
| `neutral` | 9 | 29 | 0 | 4 |
| `negative` | 1 | 10 | 176 | 5 |
| `unknown` | 5 | 5 | 4 | 28 |

## Полнота по тегам

| тег | полнота | ожидаемых кейсов |
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


Кейсы по одному — в артефакте `2026-10-23-sentiment-prompt-expanded.jsonl` рядом с этим файлом.
