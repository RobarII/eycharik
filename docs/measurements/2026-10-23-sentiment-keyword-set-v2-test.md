---
title: 'Оценка 2026-10-23: риск-радар ключевые слова set v2 test'
summary: "58 кейсов, гейты пройдены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-23 — пройдена

- команда: `python -m onboarding.evals.sentiment --provider keyword --split test --repeat 1`
- коммит: `eb70b76`
- окружение: `local`
- сплит: `test`
- кейсов: 58 (dev 58, test 0)
- повторов на кейс: 1
- вызовов: 58
- заметка: набор v2 (107 кейсов, деление на dev и test) заменяет набор v1 из 16 кейсов; эти числа несравнимы со строками v1 от 2026-10-23. Метки писал один аннотатор, каппы между аннотаторами пока нет. Правила меток: docs/evals/sentiment-guide.md.

## Качество

| метрика | значение | 95% ДИ |
|---|---|---|
| `sentiment_accuracy` | 0.345 | [0.24, 0.47] |
| `case_accuracy` | 0.345 | majority over repetitions |
| `sentiment_macro_f1` | 0.297 | — |
| `tag_precision` | 0.827 | — |
| `tag_recall` | 0.597 | — |
| `tag_f1` | 0.694 | — |
| `escalation_recall` | 0.600 | [0.31, 0.83] |
| `false_alarm_rate` | 0.188 | — |
| `fallback_rate` | 0.000 | — |
| `format_error_rate` | 0.000 | — |

## Задержка

| метрика | значение |
|---|---|
| `p50_latency_ms` | 0.0 |
| `p95_latency_ms` | 0.0 |
| `p99_latency_ms` | 0.0 |

## Полнота по тону

| тон | полнота | ожидаемых кейсов |
|---|---|---|
| `positive` | 0.125 | 16 |
| `neutral` | 0.250 | 8 |
| `negative` | 0.438 | 32 |
| `unknown` | 1.000 | 2 |

## Матрица ошибок

Строки — метка, столбцы — предсказание.

| метка \ предсказание | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 2 | 11 | 1 | 2 |
| `neutral` | 1 | 2 | 0 | 5 |
| `negative` | 0 | 14 | 14 | 4 |
| `unknown` | 0 | 0 | 0 | 2 |

## Полнота по тегам

| тег | полнота | ожидаемых кейсов |
|---|---|---|
| `access` | 0.875 | 8 |
| `manager` | 0.692 | 13 |
| `colleagues` | 0.857 | 7 |
| `workload` | 0.300 | 10 |
| `clarity` | 0.500 | 12 |
| `hr` | 0.875 | 8 |
| `it` | 0.600 | 5 |
| `integration` | 0.400 | 5 |
| `other` | 0.000 | 4 |


Кейсы по одному — в артефакте `2026-10-23-sentiment-keyword-set-v2-test.jsonl` рядом с этим файлом.
