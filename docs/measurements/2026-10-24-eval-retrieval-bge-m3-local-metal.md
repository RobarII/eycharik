---
title: "Оценка 2026-10-24: поиск на bge-m3 локально на Metal"
summary: "138 кейсов с bge-m3 в llama.cpp: recall@5 0.978, MRR 0.890, leak_rate 0.000, гейты пройдены."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-24 — пройдена

- команда: `python -m onboarding.evals --retrieval-only --write --label bge-m3-local-metal --note llama.cpp bge-m3 Q8_0, /v1/embeddings, pooling cls, embd-normalize 2, Apple M2 Metal`
- коммит: `bf10796`
- модель: `n/a`
- окружение: `local`
- провайдер эмбеддингов: `openai`
- поиск: `local-bge-m3 (bge-m3, dim 1024) + rerank:openrouter-nemotron-rerank-8b (nvidia/nemotron-3.5-rerank-8b:free) + bm25:off + contextual:off`
- артефакт: `2026-10-24-eval-retrieval-bge-m3-local-metal.jsonl`
- базовый прогон: `ff02d8b`
- заметка: llama.cpp bge-m3 Q8_0, /v1/embeddings, pooling cls, embd-normalize 2, Apple M2 Metal
- кейсов: 158
- сгенерированные ответы: False

| метрика | значение | гейт |
|---|---|---|
| `recall_at_5` | 0.978 | >= 0.95 |
| `mrr` | 0.890 | >= 0.89 |
| `leak_rate` | 0.000 | <= 0.00 |

## Страты

Один агрегат скрывает сломавшуюся страту. Гейт по стратe называется только тогда,
когда в ней не меньше 10 кейсов.

| страта | кейсов | recall@5 | context@5 | mrr | эскалация | содержит |
|---|---|---|---|---|---|---|
| `fact` | 118 | 0.98 | - | 0.90 | - | - |
| `neardup` | 5 | 1.00 | - | 0.84 | - | - |
| `multihop` | 6 | 0.92 | - | 1.00 | - | - |
| `acl` | 10 | 1.00 | - | 0.35 | - | - |
| `escalation` | 5 | 0.50 | - | 1.00 | - | - |
| `injection` | 3 | - | - | - | - | - |
| `unanswerable` | 5 | - | - | - | - | - |
| `morphology` | 6 | 1.00 | - | 0.78 | - | - |
