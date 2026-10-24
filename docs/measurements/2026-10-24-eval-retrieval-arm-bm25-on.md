---
title: "Оценка 2026-10-24: arm-bm25-on"
summary: "137 кейсов, гейты пройдены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-24 — пройдена

- команда: `python -m onboarding.evals --retrieval-only --write --label arm-bm25-on --note parade database, pg_search installed, bm25 enabled: the three-list fusion`
- коммит: `65fc273`
- модель: `n/a`
- окружение: `local`
- провайдер эмбеддингов: `openai`
- поиск: `openrouter-qwen3-embedding-8b (qwen/qwen3-embedding-8b, dim 1024) + rerank:openrouter-nemotron-rerank-8b (nvidia/nemotron-3.5-rerank-8b:free) + bm25:on + contextual:off`
- артефакт: `2026-10-24-eval-retrieval-arm-bm25-on.jsonl`
- базовый прогон: `65fc273`
- заметка: база Parade, `pg_search` установлен, bm25 включён: слияние трёх списков
- кейсов: 137
- сгенерированные ответы: False

| метрика | значение | гейт |
|---|---|---|
| `recall_at_5` | 0.988 | >= 0.96 |
| `mrr` | 0.915 | >= 0.87 |
| `leak_rate` | 0.000 | <= 0.00 |

## Страты

Одна сводка скрывает сломавшуюся страту. Гейт приводится по страте, только если
в ней не меньше десяти кейсов.

| страта | кейсов | recall@5 | context@5 | mrr | эскалация | contains |
|---|---|---|---|---|---|---|
| `fact` | 115 | 0.99 | - | 0.93 | - | - |
| `neardup` | 3 | 1.00 | - | 0.67 | - | - |
| `acl` | 10 | 1.00 | - | 0.50 | - | - |
| `escalation` | 3 | 0.50 | - | 1.00 | - | - |
| `injection` | 1 | 0.00 | - | 0.00 | - | - |
| `unanswerable` | 3 | 0.00 | - | 0.00 | - | - |
| `morphology` | 2 | 1.00 | - | 0.75 | - | - |


Кейсы по одному — в артефакте `2026-10-24-eval-retrieval-arm-bm25-on.jsonl` рядом с этим файлом.
