---
title: 'Оценка 2026-10-24: полный прогон с гейтом лексем'
summary: '137 кейсов: качество без регрессии (recall@5 0.992, MRR 0.938), оба гейта задержки провалены.'
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-24 — провалена

- команда: `python -m onboarding.evals --write --label lexical-gated-full --compare docs/measurements/2026-10-24-eval-full-baseline-v5.jsonl --note probe db, qwen3 + nemotron; lexical list gated to min(3,n) covered lexemes at weight 0.5`
- коммит: `090b5fd` + правка лексической ветки в рабочем дереве
- модель: `openai/opencode-deepseek-v4.1-flash (deepseek-v4.1-flash) @ https://opencode.ai/inference/go/v1`
- окружение: `local`
- провайдер эмбеддингов: `openai`
- поиск: `openrouter-qwen3-embedding-8b (qwen/qwen3-embedding-8b, dim 1024) + rerank:openrouter-nemotron-rerank-8b (nvidia/nemotron-3.5-rerank-8b:free) + bm25:off + contextual:off`
- артефакт: `2026-10-24-eval-full-lexical-gated-full.jsonl`
- базовый прогон: `ff02d8b`
- заметка: probe db, qwen3 + nemotron; lexical list gated to min(3,n) covered lexemes at weight 0.5
- кейсов: 137
- сгенерированные ответы: True

| метрика | значение | гейт |
|---|---|---|
| `recall_at_5` | 0.992 | >= 0.95 |
| `mrr` | 0.938 | >= 0.89 |
| `leak_rate` | 0.000 | <= 0.00 |
| `context_recall_at_5` | 1.000 | >= 0.97 |
| `context_fragment_coverage` | 0.992 | >= 0.98 |
| `p95_completion_ms` | 11238.000 | <= 8000.00 |
| `p95_answer_ms` | 26849.000 | <= 15000.00 |
| `citation_support` | 1.000 | >= 1.00 |
| `escalation_correctness` | 0.964 | >= 0.90 |
| `escalation_recall` | 1.000 | >= 0.90 |
| `escalation_precision` | 0.750 | >= 0.60 |
| `reason_accuracy` | 1.000 | >= 0.90 |
| `answer_contains` | 0.902 | >= 0.85 |
| `answer_excludes` | 1.000 | >= 1.00 |
| `cost_completion_rub` | 0.087 |  |

Проваленные гейты: p95_completion_ms, p95_answer_ms

## Страты

Один агрегат скрывает сломавшуюся страту. Гейт по стратe называется только тогда,
когда в ней не меньше 10 кейсов.

| страта | кейсов | recall@5 | context@5 | mrr | эскалация | содержит |
|---|---|---|---|---|---|---|
| `fact` | 115 | 0.99 | 1.00 | 0.94 | 0.96 | 0.90 |
| `neardup` | 3 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| `acl` | 10 | 1.00 | 1.00 | 0.67 | 1.00 | 1.00 |
| `escalation` | 3 | 1.00 | 1.00 | 1.00 | 1.00 | - |
| `injection` | 1 | 0.00 | - | 0.00 | 1.00 | - |
| `unanswerable` | 3 | 0.00 | - | 0.00 | 1.00 | - |
| `morphology` | 2 | 1.00 | 1.00 | 0.75 | 1.00 | 0.50 |

## Сравнение с базовым прогоном

Парный бутстрэп по кейсам, которые оценили оба прогона: два отдельных числа —
не сравнение, сравнение — те же кейсы, пересэмплированные вместе.

| метрика | текущий | базовый | дельта | 95% CI | p(дельта <= 0) | n |
|---|---|---|---|---|---|---|
| `recall` | 0.993 | 0.993 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `context_recall` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `rr` | 0.842 | 0.850 | -0.009 | [-0.027, +0.009] | 0.851 | 137 (-) |
| `citation_supported` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `escalation_correct` | 0.964 | 0.942 | +0.022 | [-0.022, +0.066] | 0.212 | 137 (-) |
| `escalation_matched` | 0.964 | 0.949 | +0.015 | [-0.022, +0.058] | 0.316 | 137 (-) |
| `contains_expected` | 0.912 | 0.912 | +0.000 | [-0.051, +0.051] | 0.573 | 137 (-) |
| `forbidden_clean` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
