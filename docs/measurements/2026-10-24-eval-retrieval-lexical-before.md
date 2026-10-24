---
title: 'Оценка 2026-10-24: лексическая ветка как есть'
summary: 'Проба поиска на 137 кейсах с лексической веткой plainto_tsquery AND: recall@5 0.992, MRR 0.950.'
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-24 — пройдена

- команда: `python -m onboarding.evals --retrieval-only --write --label lexical-before --note probe db with qwen3 vectors; lexical branch as shipped (plainto_tsquery AND)`
- коммит: `f9ef683`
- модель: `n/a`
- окружение: `local`
- провайдер эмбеддингов: `openai`
- поиск: `openrouter-qwen3-embedding-8b (qwen/qwen3-embedding-8b, dim 1024) + rerank:openrouter-nemotron-rerank-8b (nvidia/nemotron-3.5-rerank-8b:free) + bm25:off + contextual:off`
- артефакт: `2026-10-24-eval-retrieval-lexical-before.jsonl`
- базовый прогон: `ff02d8b`
- заметка: probe db with qwen3 vectors; lexical branch as shipped (plainto_tsquery AND)
- кейсов: 137
- сгенерированные ответы: False

| метрика | значение | гейт |
|---|---|---|
| `recall_at_5` | 0.992 | >= 0.95 |
| `mrr` | 0.950 | >= 0.89 |
| `leak_rate` | 0.000 | <= 0.00 |

## Страты

Один агрегат скрывает сломавшуюся страту. Гейт по стратe называется только тогда,
когда в ней не меньше 10 кейсов.

| страта | кейсов | recall@5 | context@5 | mrr | эскалация | содержит |
|---|---|---|---|---|---|---|
| `fact` | 115 | 0.99 | - | 0.96 | - | - |
| `neardup` | 3 | 1.00 | - | 1.00 | - | - |
| `acl` | 10 | 1.00 | - | 0.42 | - | - |
| `escalation` | 3 | 1.00 | - | 1.00 | - | - |
| `injection` | 1 | 0.00 | - | 0.00 | - | - |
| `unanswerable` | 3 | 0.00 | - | 0.00 | - | - |
| `morphology` | 2 | 1.00 | - | 0.75 | - | - |
