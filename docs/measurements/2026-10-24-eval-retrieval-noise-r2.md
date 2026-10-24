---
title: "Оценка 2026-10-24: noise-r2"
summary: "137 кейсов, гейты пройдены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-24 — пройдена

- команда: `python -m onboarding.evals --retrieval-only --write --label noise-r2`
- коммит: `332d88b`
- модель: `n/a`
- окружение: `local`
- провайдер эмбеддингов: `openai`
- поиск: `openrouter-qwen3-embedding-8b (qwen/qwen3-embedding-8b, dim 1024) + rerank:openrouter-nemotron-rerank-8b (nvidia/nemotron-3.5-rerank-8b:free) + bm25:off + contextual:off`
- артефакт: `2026-10-24-eval-retrieval-noise-r2.jsonl`
- кейсов: 137
- сгенерированные ответы: False

| метрика | значение | гейт |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.90 |
| `mrr` | 0.941 | >= 0.75 |
| `leak_rate` | 0.000 | <= 0.00 |

## Страты

Одна сводка скрывает сломавшуюся страту. Гейт приводится по страте, только если
в ней не меньше десяти кейсов.

| страта | кейсов | recall@5 | context@5 | mrr | эскалация | contains |
|---|---|---|---|---|---|---|
| `fact` | 115 | 1.00 | - | 0.95 | - | - |
| `neardup` | 3 | 1.00 | - | 1.00 | - | - |
| `acl` | 10 | 1.00 | - | 0.42 | - | - |
| `escalation` | 3 | 1.00 | - | 1.00 | - | - |
| `injection` | 1 | 0.00 | - | 0.00 | - | - |
| `unanswerable` | 3 | 0.00 | - | 0.00 | - | - |
| `morphology` | 2 | 1.00 | - | 0.75 | - | - |


Кейсы по одному — в артефакте `2026-10-24-eval-retrieval-noise-r2.jsonl` рядом с этим файлом.
