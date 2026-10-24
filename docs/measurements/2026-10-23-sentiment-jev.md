---
title: "Оценка 2026-10-23: риск-радар jev"
summary: "58 кейсов, гейты пройдены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-23 — пройдена

- команда: `python -m onboarding.evals.sentiment --provider jev --split test --repeat 3`
- коммит: `4e8901f`
- окружение: `local`
- сплит: `test`
- модель: `typesafe/jev-1.14`
- рубрика: `sentiment-jev@1`
- кейсов: 58 (dev 0, test 58)
- повторов на кейс: 3
- вызовов: 174

## Качество

| метрика | значение | 95% ДИ |
|---|---|---|
| `sentiment_accuracy` | 0.833 | [0.77, 0.88] |
| `case_accuracy` | 0.828 | majority over repetitions |
| `sentiment_macro_f1` | 0.705 | — |
| `tag_precision` | 0.533 | — |
| `tag_recall` | 0.792 | — |
| `tag_f1` | 0.637 | — |
| `escalation_recall` | 1.000 | [0.89, 1.00] |
| `false_alarm_rate` | 0.396 | — |
| `fallback_rate` | 0.000 | — |
| `format_error_rate` | 0.000 | — |

## Стоимость

| метрика | значение |
|---|---|
| `cost_rub_total` | 0.0000 |
| `cost_rub_per_1k_calls` | 0.0000 |
| `input_tokens_total` | 178965 |
| `cost_usd_total` | 0.007517 |
| `cost_usd_per_1k_calls` | 0.043198 |
| `priced_calls` | 174 / 174 |

## Задержка

| метрика | значение |
|---|---|
| `p50_latency_ms` | 348.2 |
| `p95_latency_ms` | 524.6 |
| `p99_latency_ms` | 831.8 |

## Полнота по тону

| тон | полнота | ожидаемых кейсов |
|---|---|---|
| `positive` | 0.812 | 48 |
| `neutral` | 0.625 | 24 |
| `negative` | 0.917 | 96 |
| `unknown` | 0.500 | 6 |

## Матрица ошибок

Строки — метка, столбцы — предсказание.

| метка \ предсказание | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 39 | 6 | 3 | 0 |
| `neutral` | 6 | 15 | 0 | 3 |
| `negative` | 0 | 8 | 88 | 0 |
| `unknown` | 3 | 0 | 0 | 3 |

## Полнота по тегам

| тег | полнота | ожидаемых кейсов |
|---|---|---|
| `access` | 1.000 | 24 |
| `manager` | 0.692 | 39 |
| `colleagues` | 1.000 | 21 |
| `workload` | 0.900 | 30 |
| `clarity` | 0.917 | 36 |
| `hr` | 0.875 | 24 |
| `it` | 1.000 | 15 |
| `integration` | 0.200 | 15 |
| `other` | 0.000 | 12 |


Кейсы по одному — в артефакте `2026-10-23-sentiment-jev.jsonl` рядом с этим файлом.
