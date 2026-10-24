---
title: "Оценка 2026-10-24: baseline-v2"
summary: "137 кейсов, гейты провалены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-24 — провалена

- команда: `python -m onboarding.evals --write --write-baseline --label baseline-v2 --note prompt v7 (v6 text, temperature 0), rerank deadline 6 s; quality gates pinned from this run --compare docs/measurements/2026-10-24-eval-full-prompt-v7.jsonl`
- коммит: `65fc273`
- модель: `openai/opencode-deepseek-v4.1-flash (deepseek-v4.1-flash) @ https://opencode.ai/inference/go/v1`
- окружение: `local`
- провайдер эмбеддингов: `openai`
- поиск: `openrouter-qwen3-embedding-8b (qwen/qwen3-embedding-8b, dim 1024) + rerank:openrouter-nemotron-rerank-8b (nvidia/nemotron-3.5-rerank-8b:free) + bm25:off + contextual:off`
- артефакт: `2026-10-24-eval-full-baseline-v2.jsonl`
- базовый прогон: `65fc273`
- заметка: промпт v7 (текст v6, temperature 0), срок реранка 6 с; гейты качества закреплены по этому прогону
- кейсов: 137
- сгенерированные ответы: True

| метрика | значение | гейт |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.96 |
| `mrr` | 0.937 | >= 0.88 |
| `leak_rate` | 0.000 | <= 0.00 |
| `context_recall_at_5` | 0.996 | >= 0.96 |
| `context_fragment_coverage` | 0.984 | >= 0.94 |
| `p95_completion_ms` | 11758.000 | <= 8000.00 |
| `p95_answer_ms` | 17862.000 | <= 15000.00 |
| `citation_support` | 1.000 | >= 0.97 |
| `escalation_correctness` | 0.942 | >= 0.85 |
| `escalation_recall` | 1.000 | >= 0.62 |
| `escalation_precision` | 0.682 | >= 0.36 |
| `reason_accuracy` | 0.917 | >= 0.55 |
| `answer_contains` | 0.893 | >= 0.81 |
| `answer_excludes` | 1.000 | >= 0.60 |
| `cost_completion_rub` | 0.083 |  |

Проваленные гейты: p95_completion_ms, p95_answer_ms

## Страты

Одна сводка скрывает сломавшуюся страту. Гейт приводится по страте, только если
в ней не меньше десяти кейсов.

| страта | кейсов | recall@5 | context@5 | mrr | эскалация | contains |
|---|---|---|---|---|---|---|
| `fact` | 115 | 1.00 | 1.00 | 0.95 | 0.94 | 0.90 |
| `neardup` | 3 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| `acl` | 10 | 1.00 | 1.00 | 0.42 | 1.00 | 1.00 |
| `escalation` | 3 | 1.00 | 0.50 | 1.00 | 0.67 | - |
| `injection` | 1 | 0.00 | - | 0.00 | 1.00 | - |
| `unanswerable` | 3 | 0.00 | - | 0.00 | 1.00 | - |
| `morphology` | 2 | 1.00 | 1.00 | 0.75 | 1.00 | 0.50 |

## Сравнение с базовым прогоном

Парный бутстрап по кейсам, которые прошли оба прогона: два отдельных числа — не
сравнение, сравнивать надо один и тот же набор после пересэмплирования.

| метрика | текущий | базовый | дельта | 95% ДИ | p(дельта <= 0) | n |
|---|---|---|---|---|---|---|
| `recall` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `context_recall` | 0.996 | 0.996 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `rr` | 0.841 | 0.842 | -0.001 | [-0.003, +0.000] | 1.000 | 137 (-) |
| `citation_supported` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `escalation_correct` | 0.942 | 0.964 | -0.022 | [-0.073, +0.022] | 0.864 | 137 (-) |
| `escalation_matched` | 0.949 | 0.978 | -0.029 | [-0.080, +0.015] | 0.922 | 137 (-) |
| `contains_expected` | 0.905 | 0.949 | -0.044 | [-0.095, +0.000] | 0.990 | 137 (-) |
| `forbidden_clean` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |


Кейсы по одному — в артефакте `2026-10-24-eval-full-baseline-v2.jsonl` рядом с этим файлом.
