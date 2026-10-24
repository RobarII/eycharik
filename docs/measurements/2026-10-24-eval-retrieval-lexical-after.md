---
title: 'Оценка 2026-10-24: лексическая ветка с OR'
summary: 'Проба поиска на 137 кейсах с OR по лексемам вопроса: recall@5 0.976, MRR 0.906, хуже базы.'
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-24 — пройдена

- команда: `python -m onboarding.evals --retrieval-only --write --label lexical-after --compare docs/measurements/2026-10-24-eval-retrieval-lexical-before.jsonl --note probe db with qwen3 vectors; lexical branch now ORs the question lexemes`
- коммит: `090b5fd` + правка лексической ветки в рабочем дереве
- модель: `n/a`
- окружение: `local`
- провайдер эмбеддингов: `openai`
- поиск: `openrouter-qwen3-embedding-8b (qwen/qwen3-embedding-8b, dim 1024) + rerank:openrouter-nemotron-rerank-8b (nvidia/nemotron-3.5-rerank-8b:free) + bm25:off + contextual:off`
- артефакт: `2026-10-24-eval-retrieval-lexical-after.jsonl`
- базовый прогон: `ff02d8b`
- заметка: probe db with qwen3 vectors; lexical branch now ORs the question lexemes
- кейсов: 137
- сгенерированные ответы: False

| метрика | значение | гейт |
|---|---|---|
| `recall_at_5` | 0.976 | >= 0.95 |
| `mrr` | 0.906 | >= 0.89 |
| `leak_rate` | 0.000 | <= 0.00 |

## Страты

Один агрегат скрывает сломавшуюся страту. Гейт по стратe называется только тогда,
когда в ней не меньше 10 кейсов.

| страта | кейсов | recall@5 | context@5 | mrr | эскалация | содержит |
|---|---|---|---|---|---|---|
| `fact` | 115 | 0.97 | - | 0.90 | - | - |
| `neardup` | 3 | 1.00 | - | 1.00 | - | - |
| `acl` | 10 | 1.00 | - | 1.00 | - | - |
| `escalation` | 3 | 1.00 | - | 1.00 | - | - |
| `injection` | 1 | 0.00 | - | 0.00 | - | - |
| `unanswerable` | 3 | 0.00 | - | 0.00 | - | - |
| `morphology` | 2 | 1.00 | - | 1.00 | - | - |

## Сравнение с базовым прогоном

Парный бутстрэп по кейсам, которые оценили оба прогона: два отдельных числа —
не сравнение, сравнение — те же кейсы, пересэмплированные вместе.

| метрика | текущий | базовый | дельта | 95% CI | p(дельта <= 0) | n |
|---|---|---|---|---|---|---|
| `recall` | 0.978 | 0.993 | -0.015 | [-0.036, +0.000] | 1.000 | 137 (-) |
| `context_recall` | 0.000 | 0.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `rr` | 0.814 | 0.853 | -0.039 | [-0.081, +0.002] | 0.969 | 137 (-) |
| `citation_supported` | 0.000 | 0.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `escalation_correct` | 0.000 | 0.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `escalation_matched` | 0.000 | 0.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `contains_expected` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `forbidden_clean` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
