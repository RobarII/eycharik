---
title: 'Оценка 2026-10-23: риск-радар ключевые слова set v2 dev'
summary: "49 кейсов, гейты пройдены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-23 — пройдена

- команда: `python -m onboarding.evals.sentiment --provider keyword --split dev --repeat 1`
- коммит: `eb70b76`
- окружение: `local`
- сплит: `dev`
- кейсов: 49 (dev 49, test 0)
- повторов на кейс: 1
- вызовов: 49
- заметка: набор v2 (107 кейсов, деление на dev и test) заменяет набор v1 из 16 кейсов; эти числа несравнимы со строками v1 от 2026-10-23. Метки писал один аннотатор, каппы между аннотаторами пока нет. Правила меток: docs/evals/sentiment-guide.md.

## Качество

| метрика | значение | 95% ДИ |
|---|---|---|
| `sentiment_accuracy` | 0.429 | [0.30, 0.57] |
| `case_accuracy` | 0.429 | majority over repetitions |
| `sentiment_macro_f1` | 0.390 | — |
| `tag_precision` | 0.735 | — |
| `tag_recall` | 0.600 | — |
| `tag_f1` | 0.661 | — |
| `escalation_recall` | 0.400 | [0.12, 0.77] |
| `false_alarm_rate` | 0.136 | — |
| `fallback_rate` | 0.000 | — |
| `format_error_rate` | 0.000 | — |

## Задержка

| метрика | значение |
|---|---|
| `p50_latency_ms` | 0.0 |
| `p95_latency_ms` | 0.0 |
| `p99_latency_ms` | 0.2 |

## Полнота по тону

| тон | полнота | ожидаемых кейсов |
|---|---|---|
| `positive` | 0.125 | 8 |
| `neutral` | 0.818 | 11 |
| `negative` | 0.296 | 27 |
| `unknown` | 1.000 | 3 |

## Матрица ошибок

Строки — метка, столбцы — предсказание.

| метка \ предсказание | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 1 | 4 | 0 | 3 |
| `neutral` | 1 | 9 | 0 | 1 |
| `negative` | 2 | 14 | 8 | 3 |
| `unknown` | 0 | 0 | 0 | 3 |

## Полнота по тегам

| тег | полнота | ожидаемых кейсов |
|---|---|---|
| `access` | 0.800 | 5 |
| `manager` | 0.625 | 8 |
| `colleagues` | 0.889 | 9 |
| `workload` | 0.375 | 8 |
| `clarity` | 0.636 | 11 |
| `hr` | 0.500 | 6 |
| `it` | 0.800 | 5 |
| `integration` | 0.333 | 6 |
| `other` | 0.000 | 2 |


Кейсы по одному — в артефакте `2026-10-23-sentiment-keyword-set-v2-dev.jsonl` рядом с этим файлом.
