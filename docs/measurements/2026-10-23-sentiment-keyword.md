---
title: "Оценка 2026-10-23: риск-радар ключевые слова"
summary: "58 кейсов, гейты пройдены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-23 — пройдена

- команда: `python -m onboarding.evals.sentiment --provider keyword --split test --repeat 3`
- коммит: `c0585bc`
- окружение: `local`
- сплит: `test`
- модель: `deterministic`
- рубрика: `—`
- кейсов: 58 (dev 0, test 58)
- повторов на кейс: 3
- вызовов: 174

## Качество

| метрика | значение | 95% ДИ |
|---|---|---|
| `sentiment_accuracy` | 0.345 | [0.28, 0.42] |
| `case_accuracy` | 0.345 | majority over repetitions |
| `sentiment_macro_f1` | 0.297 | — |
| `tag_precision` | 0.827 | — |
| `tag_recall` | 0.597 | — |
| `tag_f1` | 0.694 | — |
| `escalation_recall` | 0.600 | [0.42, 0.75] |
| `false_alarm_rate` | 0.188 | — |
| `fallback_rate` | 0.000 | — |
| `format_error_rate` | 0.000 | — |

## Стоимость

| метрика | значение |
|---|---|
| `cost_rub_total` | 0.0000 |
| `cost_rub_per_1k_calls` | 0.0000 |
| `input_tokens_total` | 0 |
| `cost_usd_total` | 0.000000 |
| `cost_usd_per_1k_calls` | 0.000000 |
| `priced_calls` | 0 / 174 |

## Задержка

| метрика | значение |
|---|---|
| `p50_latency_ms` | 0.0 |
| `p95_latency_ms` | 0.0 |
| `p99_latency_ms` | 0.0 |

## Полнота по тону

| тон | полнота | ожидаемых кейсов |
|---|---|---|
| `positive` | 0.125 | 48 |
| `neutral` | 0.250 | 24 |
| `negative` | 0.438 | 96 |
| `unknown` | 1.000 | 6 |

## Матрица ошибок

Строки — метка, столбцы — предсказание.

| метка \ предсказание | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 6 | 33 | 3 | 6 |
| `neutral` | 3 | 6 | 0 | 15 |
| `negative` | 0 | 42 | 42 | 12 |
| `unknown` | 0 | 0 | 0 | 6 |

## Полнота по тегам

| тег | полнота | ожидаемых кейсов |
|---|---|---|
| `access` | 0.875 | 24 |
| `manager` | 0.692 | 39 |
| `colleagues` | 0.857 | 21 |
| `workload` | 0.300 | 30 |
| `clarity` | 0.500 | 36 |
| `hr` | 0.875 | 24 |
| `it` | 0.600 | 15 |
| `integration` | 0.400 | 15 |
| `other` | 0.000 | 12 |


Кейсы по одному — в артефакте `2026-10-23-sentiment-keyword.jsonl` рядом с этим файлом.
