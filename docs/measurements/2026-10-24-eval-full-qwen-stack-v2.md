---
title: 'Оценка 2026-10-24: 155 кейсов на стеке qwen3 + deepseek'
summary: 'Полный прогон после роста золотого набора и температуры 0: гейты пройдены, ложные эскалации упали, мультихоп-страта показывает 0.333 по содержанию.'
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-24 — пройдена

- команда: `python -m onboarding.evals --write --label qwen-stack-v2 --compare docs/measurements/2026-10-24-eval-full-baseline-v5.jsonl --note golden set grown to 155: multihop, morphology, injection and unanswerable strata filled; answer temperature 0 for reproducibility`
- коммит: `cc2e85d`
- модель: `openai/opencode-deepseek-v4.1-flash (deepseek-v4.1-flash) @ https://opencode.ai/inference/go/v1`
- окружение: `local`
- провайдер эмбеддингов: `openai`
- поиск: `openrouter-qwen3-embedding-8b (qwen/qwen3-embedding-8b, dim 1024) + rerank:openrouter-qwen3-reranker-8b (qwen/qwen3-reranker-8b) + bm25:off + contextual:off`
- артефакт: `2026-10-24-eval-full-qwen-stack-v2.jsonl`
- базовый прогон: `ff02d8b`
- заметка: golden set grown to 155: multihop, morphology, injection and unanswerable strata filled; answer temperature 0 for reproducibility
- кейсов: 155
- сгенерированные ответы: True

| метрика | значение | гейт |
|---|---|---|
| `recall_at_5` | 0.989 | >= 0.95 |
| `mrr` | 0.935 | >= 0.89 |
| `leak_rate` | 0.000 | <= 0.00 |
| `context_recall_at_5` | 1.000 | >= 0.97 |
| `context_fragment_coverage` | 0.985 | >= 0.98 |
| `p95_completion_ms` | 11058 | диагностика |
| `p95_answer_ms` | 17869 | диагностика |
| `citation_support` | 1.000 | >= 1.00 |
| `escalation_correctness` | 0.981 | >= 0.90 |
| `escalation_recall` | 1.000 | >= 0.90 |
| `escalation_precision` | 0.913 | >= 0.60 |
| `reason_accuracy` | 0.938 | >= 0.90 |
| `answer_contains` | 0.940 | >= 0.85 |
| `answer_excludes` | 1.000 | >= 1.00 |
| `cost_completion_rub` | 0.083 |  |

## Задержка — диагностика

Полный контур этого прогона выходит за границу, которую называет ADR 0030, поэтому бюджет `p95` здесь не гейт: он измеряет шлюз, а не систему. Гейт задержки действует на профилях с `personal_data: true`.

## Страты

Один агрегат скрывает сломавшуюся страту. Гейт по стратe называется только тогда,
когда в ней не меньше 10 кейсов.

| страта | кейсов | recall@5 | context@5 | mrr | эскалация | содержит |
|---|---|---|---|---|---|---|
| `fact` | 115 | 0.99 | 1.00 | 0.94 | 0.99 | 0.97 |
| `neardup` | 5 | 1.00 | 1.00 | 0.90 | 1.00 | 1.00 |
| `multihop` | 6 | 0.92 | 1.00 | 1.00 | 0.83 | 0.33 |
| `acl` | 10 | 1.00 | 1.00 | 0.67 | 1.00 | 1.00 |
| `escalation` | 5 | 1.00 | 1.00 | 1.00 | 0.80 | - |
| `injection` | 3 | - | - | - | 1.00 | - |
| `unanswerable` | 5 | - | - | - | 1.00 | - |
| `morphology` | 6 | 1.00 | 1.00 | 0.81 | 1.00 | 0.83 |

## Сравнение с базовым прогоном

Парный бутстрэп по кейсам, которые оценили оба прогона: два отдельных числа —
не сравнение, сравнение — те же кейсы, пересэмплированные вместе.

| метрика | текущий | базовый | дельта | 95% CI | p(дельта <= 0) | n |
|---|---|---|---|---|---|---|
| `recall` | 0.993 | 0.993 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `context_recall` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `rr` | 0.842 | 0.850 | -0.009 | [-0.027, +0.009] | 0.851 | 137 (-) |
| `citation_supported` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `escalation_correct` | 0.985 | 0.942 | +0.044 | [+0.007, +0.088] | 0.018 | 137 (-) |
| `escalation_matched` | 0.993 | 0.949 | +0.044 | [+0.007, +0.088] | 0.018 | 137 (-) |
| `contains_expected` | 0.971 | 0.912 | +0.058 | [+0.007, +0.109] | 0.016 | 137 (-) |
| `forbidden_clean` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
