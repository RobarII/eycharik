---
title: "Оценка 2026-10-23: риск-радар jev расширенный набор v1"
summary: "114 кейсов, гейты пройдены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-23 — пройдена

- команда: `python -m onboarding.evals.sentiment --provider jev --split test --repeat 3`
- коммит: `460d91f`
- окружение: `local`
- сплит: `test`
- модель: `typesafe/jev-1.14`
- рубрика: `sentiment-jev@1`
- кейсов: 114 (dev 0, test 114)
- повторов на кейс: 3
- вызовов: 342

## Качество

| метрика | значение | 95% ДИ |
|---|---|---|
| `sentiment_accuracy` | 0.877 | [0.84, 0.91] |
| `case_accuracy` | 0.877 | majority over repetitions |
| `sentiment_macro_f1` | 0.807 | — |
| `tag_precision` | 0.488 | — |
| `tag_recall` | 0.738 | — |
| `tag_f1` | 0.587 | — |
| `escalation_recall` | 0.971 | [0.92, 0.99] |
| `false_alarm_rate` | 0.338 | — |
| `fallback_rate` | 0.000 | — |
| `format_error_rate` | 0.000 | — |

## Стоимость

| метрика | значение |
|---|---|
| `cost_rub_total` | 0.0000 |
| `cost_rub_per_1k_calls` | 0.0000 |
| `input_tokens_total` | 350028 |
| `cost_usd_total` | 0.014701 |
| `cost_usd_per_1k_calls` | 0.042986 |
| `priced_calls` | 342 / 342 |

## Задержка

| метрика | значение |
|---|---|
| `p50_latency_ms` | 320.1 |
| `p95_latency_ms` | 492.6 |
| `p99_latency_ms` | 570.2 |

## Полнота по тону

| тон | полнота | ожидаемых кейсов |
|---|---|---|
| `positive` | 0.864 | 66 |
| `neutral` | 0.643 | 42 |
| `negative` | 0.953 | 192 |
| `unknown` | 0.786 | 42 |

## Матрица ошибок

Строки — метка, столбцы — предсказание.

| метка \ предсказание | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 57 | 6 | 3 | 0 |
| `neutral` | 9 | 27 | 0 | 6 |
| `negative` | 0 | 9 | 183 | 0 |
| `unknown` | 6 | 3 | 0 | 33 |

## Полнота по тегам

| тег | полнота | ожидаемых кейсов |
|---|---|---|
| `access` | 0.917 | 36 |
| `manager` | 0.538 | 78 |
| `colleagues` | 1.000 | 42 |
| `workload` | 0.882 | 51 |
| `clarity` | 0.941 | 51 |
| `hr` | 0.784 | 51 |
| `it` | 1.000 | 24 |
| `integration` | 0.238 | 21 |
| `other` | 0.000 | 24 |


Кейсы по одному — в артефакте `2026-10-23-sentiment-jev-expanded-v1.jsonl` рядом с этим файлом.
