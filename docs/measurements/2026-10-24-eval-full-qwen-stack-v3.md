---
title: 'Оценка 2026-10-24: 155 кейсов на стеке qwen3 + deepseek, промпт v8'
summary: 'Полный прогон с промптом v8: провален один гейт reason_accuracy, мультихоп по содержанию 0.67; команда и коммит в шапке.'
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-24 — провалена

- команда: `python -m onboarding.evals --write --label qwen-stack-v3 --compare docs/measurements/2026-10-24-eval-full-qwen-stack-v2.jsonl --note prompt v8: a two-part question is answered part by part; golden set fixes for two multihop expectations that demanded an inflected form`
- коммит: `2009a8f`
- модель: `openai/opencode-deepseek-v4.1-flash (deepseek-v4.1-flash) @ https://opencode.ai/inference/go/v1`
- окружение: `local`
- провайдер эмбеддингов: `openai`
- поиск: `openrouter-qwen3-embedding-8b (qwen/qwen3-embedding-8b, dim 1024) + rerank:openrouter-qwen3-reranker-8b (qwen/qwen3-reranker-8b) + bm25:off + contextual:off`
- артефакт: `2026-10-24-eval-full-qwen-stack-v3.jsonl`
- базовый прогон: `ff02d8b`
- заметка: prompt v8: a two-part question is answered part by part; golden set fixes for two multihop expectations that demanded an inflected form
- кейсов: 155
- сгенерированные ответы: True

| метрика | значение | гейт |
|---|---|---|
| `recall_at_5` | 0.981 | >= 0.95 |
| `mrr` | 0.932 | >= 0.89 |
| `leak_rate` | 0.000 | <= 0.00 |
| `context_recall_at_5` | 1.000 | >= 0.97 |
| `context_fragment_coverage` | 0.985 | >= 0.98 |
| `p95_completion_ms` | 11671 | диагностика |
| `p95_answer_ms` | 16687 | диагностика |
| `citation_support` | 1.000 | >= 1.00 |
| `escalation_correctness` | 0.942 | >= 0.90 |
| `escalation_recall` | 1.000 | >= 0.90 |
| `escalation_precision` | 0.750 | >= 0.60 |
| `reason_accuracy` | 0.875 | >= 0.90 |
| `answer_contains` | 0.896 | >= 0.85 |
| `answer_excludes` | 1.000 | >= 1.00 |
| `cost_completion_rub` | 0.084 |  |

Проваленные гейты: reason_accuracy

## Задержка — диагностика

Полный контур этого прогона выходит за границу, которую называет ADR 0030, поэтому бюджет `p95` здесь не гейт: он измеряет шлюз, а не систему. Гейт задержки действует на профилях с `personal_data: true`.

## Страты

Один агрегат скрывает сломавшуюся страту. Гейт по стратe называется только тогда,
когда в ней не меньше 10 кейсов.

| страта | кейсов | recall@5 | context@5 | mrr | эскалация | содержит |
|---|---|---|---|---|---|---|
| `fact` | 115 | 0.98 | 1.00 | 0.94 | 0.96 | 0.90 |
| `neardup` | 5 | 1.00 | 1.00 | 0.90 | 0.80 | 0.80 |
| `multihop` | 6 | 0.92 | 1.00 | 1.00 | 0.83 | 0.67 |
| `acl` | 10 | 1.00 | 1.00 | 0.67 | 0.90 | 1.00 |
| `escalation` | 5 | 1.00 | 1.00 | 1.00 | 0.80 | - |
| `injection` | 3 | - | - | - | 1.00 | - |
| `unanswerable` | 5 | - | - | - | 1.00 | - |
| `morphology` | 6 | 1.00 | 1.00 | 0.81 | 1.00 | 1.00 |

## Сравнение с базовым прогоном

Парный бутстрэп по кейсам, которые оценили оба прогона: два отдельных числа —
не сравнение, сравнение — те же кейсы, пересэмплированные вместе.

| метрика | текущий | базовый | дельта | 95% CI | p(дельта <= 0) | n |
|---|---|---|---|---|---|---|
| `recall` | 0.984 | 0.990 | -0.006 | [-0.019, +0.000] | 1.000 | 154 (-) |
| `context_recall` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 154 (-) |
| `rr` | 0.811 | 0.813 | -0.002 | [-0.006, +0.000] | 1.000 | 154 (-) |
| `citation_supported` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 154 (-) |
| `escalation_correct` | 0.942 | 0.981 | -0.039 | [-0.078, +0.000] | 0.987 | 154 (-) |
| `escalation_matched` | 0.955 | 0.987 | -0.032 | [-0.071, +0.000] | 0.976 | 154 (-) |
| `contains_expected` | 0.909 | 0.955 | -0.045 | [-0.097, +0.006] | 0.969 | 154 (-) |
| `forbidden_clean` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 154 (-) |
