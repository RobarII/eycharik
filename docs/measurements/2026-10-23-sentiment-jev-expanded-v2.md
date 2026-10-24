---
title: "Оценка 2026-10-23: риск-радар jev расширенный набор v2"
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
- рубрика: `sentiment-jev@2`
- кейсов: 114 (dev 0, test 114)
- повторов на кейс: 3
- вызовов: 342

## Качество

| метрика | значение | 95% ДИ |
|---|---|---|
| `sentiment_accuracy` | 0.883 | [0.84, 0.91] |
| `case_accuracy` | 0.886 | majority over repetitions |
| `sentiment_macro_f1` | 0.812 | — |
| `tag_precision` | 0.567 | — |
| `tag_recall` | 0.698 | — |
| `tag_f1` | 0.626 | — |
| `escalation_recall` | 0.951 | [0.89, 0.98] |
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
| `p50_latency_ms` | 341.8 |
| `p95_latency_ms` | 520.4 |
| `p99_latency_ms` | 948.0 |

## Полнота по тону

| тон | полнота | ожидаемых кейсов |
|---|---|---|
| `positive` | 0.864 | 66 |
| `neutral` | 0.643 | 42 |
| `negative` | 0.964 | 192 |
| `unknown` | 0.786 | 42 |

## Матрица ошибок

Строки — метка, столбцы — предсказание.

| метка \ предсказание | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 57 | 6 | 3 | 0 |
| `neutral` | 9 | 27 | 0 | 6 |
| `negative` | 0 | 7 | 185 | 0 |
| `unknown` | 6 | 3 | 0 | 33 |

## Полнота по тегам

| тег | полнота | ожидаемых кейсов |
|---|---|---|
| `access` | 0.833 | 36 |
| `manager` | 0.500 | 78 |
| `colleagues` | 1.000 | 42 |
| `workload` | 0.882 | 51 |
| `clarity` | 0.941 | 51 |
| `hr` | 0.647 | 51 |
| `it` | 1.000 | 24 |
| `integration` | 0.143 | 21 |
| `other` | 0.000 | 24 |


Кейсы по одному — в артефакте `2026-10-23-sentiment-jev-expanded-v2.jsonl` рядом с этим файлом.
