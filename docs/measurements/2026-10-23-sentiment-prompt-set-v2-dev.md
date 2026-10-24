---
title: 'Оценка 2026-10-23: риск-радар промпт set v2 dev'
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
| `sentiment_accuracy` | 0.816 | [0.69, 0.90] |
| `case_accuracy` | 0.816 | majority over repetitions |
| `sentiment_macro_f1` | 0.743 | — |
| `tag_precision` | 0.623 | — |
| `tag_recall` | 0.717 | — |
| `tag_f1` | 0.667 | — |
| `escalation_recall` | 0.800 | [0.38, 0.96] |
| `false_alarm_rate` | 0.409 | — |
| `fallback_rate` | 0.245 | — |
| `format_error_rate` | 0.000 | — |

## Задержка

| метрика | значение |
|---|---|
| `p50_latency_ms` | 1438.5 |
| `p95_latency_ms` | 5555.3 |
| `p99_latency_ms` | 7409.0 |

## Полнота по тону

| тон | полнота | ожидаемых кейсов |
|---|---|---|
| `positive` | 0.875 | 8 |
| `neutral` | 0.818 | 11 |
| `negative` | 0.815 | 27 |
| `unknown` | 0.667 | 3 |

## Матрица ошибок

Строки — метка, столбцы — предсказание.

| метка \ предсказание | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 7 | 1 | 0 | 0 |
| `neutral` | 1 | 9 | 0 | 1 |
| `negative` | 0 | 3 | 22 | 2 |
| `unknown` | 1 | 0 | 0 | 2 |

## Полнота по тегам

| тег | полнота | ожидаемых кейсов |
|---|---|---|
| `access` | 0.800 | 5 |
| `manager` | 0.750 | 8 |
| `colleagues` | 0.778 | 9 |
| `workload` | 0.750 | 8 |
| `clarity` | 0.727 | 11 |
| `hr` | 0.667 | 6 |
| `it` | 0.800 | 5 |
| `integration` | 0.500 | 6 |
| `other` | 0.500 | 2 |


Кейсы по одному — в артефакте `2026-10-23-sentiment-prompt-set-v2-dev.jsonl` рядом с этим файлом.
