---
title: 'Оценка 2026-10-23: риск-радар промпт set v2 test'
summary: "58 кейсов, гейты пройдены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-23 — пройдена

- команда: `python -m onboarding.evals.sentiment --provider keyword --split test --repeat 1 --compare docs/measurements/2026-10-23-sentiment-keyword-set-v2-test.jsonl`
- коммит: `eb70b76`
- окружение: `local`
- сплит: `test`
- кейсов: 58 (dev 58, test 0)
- повторов на кейс: 3
- вызовов: 174
- заметка: набор v2 (107 кейсов, деление на dev и test) заменяет набор v1 из 16 кейсов; эти числа несравнимы со строками v1 от 2026-10-23. Метки писал один аннотатор, каппы между аннотаторами пока нет. Правила меток: docs/evals/sentiment-guide.md.

## Качество

| метрика | значение | 95% ДИ |
|---|---|---|
| `sentiment_accuracy` | 0.770 | [0.70, 0.83] |
| `case_accuracy` | 0.793 | majority over repetitions |
| `sentiment_macro_f1` | 0.606 | — |
| `tag_precision` | 0.740 | — |
| `tag_recall` | 0.829 | — |
| `tag_f1` | 0.782 | — |
| `escalation_recall` | 0.800 | [0.63, 0.90] |
| `false_alarm_rate` | 0.403 | — |
| `fallback_rate` | 0.195 | — |
| `format_error_rate` | 0.000 | — |

## Задержка

| метрика | значение |
|---|---|
| `p50_latency_ms` | 1354.6 |
| `p95_latency_ms` | 2673.7 |
| `p99_latency_ms` | 3994.4 |

## Полнота по тону

| тон | полнота | ожидаемых кейсов |
|---|---|---|
| `positive` | 0.771 | 48 |
| `neutral` | 0.500 | 24 |
| `negative` | 0.854 | 96 |
| `unknown` | 0.500 | 6 |

## Матрица ошибок

Строки — метка, столбцы — предсказание.

| метка \ предсказание | positive | neutral | negative | unknown |
|---|---|---|---|---|
| `positive` | 37 | 10 | 0 | 1 |
| `neutral` | 7 | 12 | 0 | 5 |
| `negative` | 0 | 6 | 82 | 8 |
| `unknown` | 2 | 0 | 1 | 3 |

## Полнота по тегам

| тег | полнота | ожидаемых кейсов |
|---|---|---|
| `access` | 1.000 | 24 |
| `manager` | 0.821 | 39 |
| `colleagues` | 0.857 | 21 |
| `workload` | 0.800 | 30 |
| `clarity` | 0.833 | 36 |
| `hr` | 0.792 | 24 |
| `it` | 0.867 | 15 |
| `integration` | 0.800 | 15 |
| `other` | 0.583 | 12 |

## Сравнение

- метрика: `case_accuracy`
- парных кейсов: 58
- базовый прогон: 0.345
- кандидат: 0.776
- дельта: +0.431 (95% bootstrap CI [0.29, 0.57])
- p(delta <= 0): 0.000
- чтение: кандидат лучше


Кейсы по одному — в артефакте `2026-10-23-sentiment-prompt-set-v2-test.jsonl` рядом с этим файлом.
