---
title: "Оценка 2026-10-24: baseline-v1"
summary: "137 кейсов, гейты провалены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-24 — провалена

- команда: `python -m onboarding.evals --write-baseline --write --label baseline-v1 --note baseline pinned from the first full run with honest metric names`
- коммит: `332d88b`
- модель: `openai/opencode-deepseek-v4.1-flash (deepseek-v4.1-flash) @ https://opencode.ai/inference/go/v1`
- окружение: `local`
- провайдер эмбеддингов: `openai`
- поиск: `openrouter-qwen3-embedding-8b (qwen/qwen3-embedding-8b, dim 1024) + rerank:openrouter-nemotron-rerank-8b (nvidia/nemotron-3.5-rerank-8b:free) + bm25:off + contextual:off`
- артефакт: `2026-10-24-eval-full-baseline-v1.jsonl`
- заметка: базовый прогон закреплён по первому полному прогону с честными именами метрик
- кейсов: 137
- сгенерированные ответы: True

| метрика | значение | гейт |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.90 |
| `mrr` | 0.937 | >= 0.75 |
| `leak_rate` | 0.000 | <= 0.00 |
| `context_recall_at_5` | 0.996 | >= 0.90 |
| `context_fragment_coverage` | 0.984 | >= 0.98 |
| `p95_completion_ms` | 10116.000 | <= 8000.00 |
| `p95_answer_ms` | 14063.000 | <= 15000.00 |
| `citation_support` | 1.000 | >= 1.00 |
| `escalation_correctness` | 0.942 | >= 0.90 |
| `escalation_recall` | 0.933 | >= 0.90 |
| `escalation_precision` | 0.737 | >= 0.90 |
| `reason_accuracy` | 0.750 | >= 0.90 |
| `answer_contains` | 0.934 | >= 1.00 |
| `answer_excludes` | 1.000 | >= 1.00 |
| `cost_completion_rub` | 0.089 |  |

Проваленные гейты: answer_contains, escalation_precision, reason_accuracy, p95_completion_ms

## Страты

Одна сводка скрывает сломавшуюся страту. Гейт приводится по страте, только если
в ней не меньше десяти кейсов.

| страта | кейсов | recall@5 | context@5 | mrr | эскалация | contains |
|---|---|---|---|---|---|---|
| `fact` | 115 | 1.00 | 1.00 | 0.95 | 0.96 | 0.94 |
| `neardup` | 3 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| `acl` | 10 | 1.00 | 1.00 | 0.42 | 0.70 | 1.00 |
| `escalation` | 3 | 1.00 | 0.50 | 1.00 | 1.00 | - |
| `injection` | 1 | 0.00 | - | 0.00 | 1.00 | - |
| `unanswerable` | 3 | 0.00 | - | 0.00 | 1.00 | - |
| `morphology` | 2 | 1.00 | 1.00 | 0.75 | 1.00 | 0.50 |


Кейсы по одному — в артефакте `2026-10-24-eval-full-baseline-v1.jsonl` рядом с этим файлом.
