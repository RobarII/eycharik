---
title: 'Оценка 2026-10-24: полный прогон на стеке qwen3 + deepseek'
summary: '137 кейсов на qwen3-embedding-8b, qwen3-reranker-8b и deepseek-v4.1-flash: гейты качества пройдены, задержка — диагностика.'
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-24 — пройдена

- команда: `python -m onboarding.evals --write --label qwen-stack-full --compare docs/measurements/2026-10-24-eval-full-baseline-v5.jsonl --note probe db; qwen3-embedding-8b + qwen3-reranker-8b + deepseek-v4.1-flash; demo gateway, latency reported not gated (ADR 0032)`
- коммит: `060281c`
- модель: `openai/opencode-deepseek-v4.1-flash (deepseek-v4.1-flash) @ https://opencode.ai/inference/go/v1`
- окружение: `local`
- провайдер эмбеддингов: `openai`
- поиск: `openrouter-qwen3-embedding-8b (qwen/qwen3-embedding-8b, dim 1024) + rerank:openrouter-qwen3-reranker-8b (qwen/qwen3-reranker-8b) + bm25:off + contextual:off`
- артефакт: `2026-10-24-eval-full-qwen-stack-full.jsonl`
- базовый прогон: `ff02d8b`
- заметка: probe db; qwen3-embedding-8b + qwen3-reranker-8b + deepseek-v4.1-flash; demo gateway, latency reported not gated (ADR 0032)
- кейсов: 137
- сгенерированные ответы: True

| метрика | значение | гейт |
|---|---|---|
| `recall_at_5` | 0.992 | >= 0.95 |
| `mrr` | 0.938 | >= 0.89 |
| `leak_rate` | 0.000 | <= 0.00 |
| `context_recall_at_5` | 1.000 | >= 0.97 |
| `context_fragment_coverage` | 0.984 | >= 0.98 |
| `p95_completion_ms` | 10936 | диагностика |
| `p95_answer_ms` | 22100 | диагностика |
| `citation_support` | 1.000 | >= 1.00 |
| `escalation_correctness` | 0.942 | >= 0.90 |
| `escalation_recall` | 0.933 | >= 0.90 |
| `escalation_precision` | 0.667 | >= 0.60 |
| `reason_accuracy` | 1.000 | >= 0.90 |
| `answer_contains` | 0.902 | >= 0.85 |
| `answer_excludes` | 1.000 | >= 1.00 |
| `cost_completion_rub` | 0.080 |  |

## Задержка — диагностика

Полный контур этого прогона выходит за границу, которую называет ADR 0030, поэтому бюджет `p95` здесь не гейт: он измеряет шлюз, а не систему. Гейт задержки действует на профилях с `personal_data: true`.

## Страты

Один агрегат скрывает сломавшуюся страту. Гейт по стратe называется только тогда,
когда в ней не меньше 10 кейсов.

| страта | кейсов | recall@5 | context@5 | mrr | эскалация | содержит |
|---|---|---|---|---|---|---|
| `fact` | 115 | 0.99 | 1.00 | 0.94 | 0.95 | 0.91 |
| `neardup` | 3 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| `acl` | 10 | 1.00 | 1.00 | 0.67 | 0.90 | 0.50 |
| `escalation` | 3 | 1.00 | 1.00 | 1.00 | 1.00 | - |
| `injection` | 1 | 0.00 | - | 0.00 | 1.00 | - |
| `unanswerable` | 3 | 0.00 | - | 0.00 | 0.67 | - |
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
| `escalation_correct` | 0.942 | 0.942 | +0.000 | [-0.044, +0.036] | 0.576 | 137 (-) |
| `escalation_matched` | 0.942 | 0.949 | -0.007 | [-0.044, +0.029] | 0.716 | 137 (-) |
| `contains_expected` | 0.912 | 0.912 | +0.000 | [-0.051, +0.051] | 0.565 | 137 (-) |
| `forbidden_clean` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
