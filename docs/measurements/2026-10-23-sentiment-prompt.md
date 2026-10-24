---
title: "Оценка 2026-10-23: риск-радар промпт"
summary: "58 кейсов, гейты пройдены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-23 — пройдена

- команда: `python -m onboarding.evals.sentiment --provider prompt --split test --repeat 1`
- коммит: `c0585bc`
- окружение: `local`
- сплит: `test`
- модель: `opencode-deepseek-v4.1-flash`
- рубрика: `—`
- кейсов: 58 (dev 0, test 58)
- повторов на кейс: 1
- вызовов: 58

## Качество

| метрика | значение | 95% ДИ |
|---|---|---|
| `sentiment_accuracy` | 0.741 | [0.62, 0.84] |
| `case_accuracy` | 0.741 | majority over repetitions |
| `sentiment_macro_f1` | 0.577 | — |
| `tag_precision` | 0.750 | — |
| `tag_recall` | 0.792 | — |
| `tag_f1` | 0.770 | — |
| `escalation_recall` | 0.700 | [0.40, 0.89] |
| `false_alarm_rate` | 0.375 | — |
| `fallback_rate` | 0.224 | — |
| `format_error_rate` | 0.000 | — |

## Стоимость

| метрика | значение |
|---|---|
| `cost_rub_total` | 0.0000 |
| `cost_rub_per_1k_calls` | 0.0000 |
| `input_tokens_total` | 0 |
| `cost_usd_total` | 0.000000 |
| `cost_usd_per_1k_calls` | 0.000000 |
| `priced_calls` | 0 / 58 |

## Задержка

| метрика | значение |
|---|---|
| `p50_latency_ms` | 1366.4 |
| `p95_latency_ms` | 4701.1 |
| `p99_latency_ms` | 5637.5 |

## Полнота по тону

| тон | полнота | ожидаемых кейсов |
|---|---|---|
| `positive` | 0.875 | 16 |
| `neutral` | 0.375 | 8 |
| `negative` | 0.781 | 32 |
| `unknown` | 0.500 | 2 |

## Матрица ошибок

Строки — метка, столбцы — предсказание.

| метка \ предсказание | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 14 | 1 | 1 | 0 |
| `neutral` | 2 | 3 | 0 | 3 |
| `negative` | 1 | 3 | 25 | 3 |
| `unknown` | 1 | 0 | 0 | 1 |

## Полнота по тегам

| тег | полнота | ожидаемых кейсов |
|---|---|---|
| `access` | 1.000 | 8 |
| `manager` | 0.769 | 13 |
| `colleagues` | 1.000 | 7 |
| `workload` | 0.700 | 10 |
| `clarity` | 0.750 | 12 |
| `hr` | 0.875 | 8 |
| `it` | 0.800 | 5 |
| `integration` | 0.800 | 5 |
| `other` | 0.250 | 4 |


Кейсы по одному — в артефакте `2026-10-23-sentiment-prompt.jsonl` рядом с этим файлом.
