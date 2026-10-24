---
title: "Оценка 2026-10-24: baseline-v5"
summary: "137 кейсов, гейты провалены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-24 — провалена

- команда: `python -m onboarding.evals --write --write-baseline --label baseline-v5 --note prompt v7 at temperature 0; gates set below the measured three-run spread; strata pin only recall floors above policy --compare docs/measurements/2026-10-24-eval-full-baseline-v4.jsonl`
- коммит: `ff02d8b`
- модель: `openai/opencode-deepseek-v4.1-flash (deepseek-v4.1-flash) @ https://opencode.ai/inference/go/v1`
- окружение: `local`
- провайдер эмбеддингов: `openai`
- поиск: `openrouter-qwen3-embedding-8b (qwen/qwen3-embedding-8b, dim 1024) + rerank:openrouter-nemotron-rerank-8b (nvidia/nemotron-3.5-rerank-8b:free) + bm25:off + contextual:off`
- артефакт: `2026-10-24-eval-full-baseline-v5.jsonl`
- заметка: промпт v7 при temperature 0; гейты ниже измеренного разброса трёх прогонов; страты закрепляют только пороги полноты выше политики
- кейсов: 137
- сгенерированные ответы: True

| метрика | значение | гейт |
|---|---|---|
| `recall_at_5` | 0.992 | >= 0.90 |
| `mrr` | 0.947 | >= 0.75 |
| `leak_rate` | 0.000 | <= 0.00 |
| `context_recall_at_5` | 1.000 | >= 0.90 |
| `context_fragment_coverage` | 0.992 | >= 0.98 |
| `p95_completion_ms` | 14093.000 | <= 8000.00 |
| `p95_answer_ms` | 29066.000 | <= 15000.00 |
| `citation_support` | 1.000 | >= 1.00 |
| `escalation_correctness` | 0.942 | >= 0.90 |
| `escalation_recall` | 0.933 | >= 0.90 |
| `escalation_precision` | 0.700 | >= 0.60 |
| `reason_accuracy` | 0.917 | >= 0.90 |
| `answer_contains` | 0.902 | >= 0.85 |
| `answer_excludes` | 1.000 | >= 1.00 |
| `cost_completion_rub` | 0.081 |  |

Проваленные гейты: p95_completion_ms, p95_answer_ms

## Страты

Одна сводка скрывает сломавшуюся страту. Гейт приводится по страте, только если
в ней не меньше десяти кейсов.

| страта | кейсов | recall@5 | context@5 | mrr | эскалация | contains |
|---|---|---|---|---|---|---|
| `fact` | 115 | 0.99 | 1.00 | 0.96 | 0.96 | 0.91 |
| `neardup` | 3 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| `acl` | 10 | 1.00 | 1.00 | 0.50 | 0.90 | 0.50 |
| `escalation` | 3 | 1.00 | 1.00 | 1.00 | 0.67 | - |
| `injection` | 1 | 0.00 | - | 0.00 | 1.00 | - |
| `unanswerable` | 3 | 0.00 | - | 0.00 | 0.67 | - |
| `morphology` | 2 | 1.00 | 1.00 | 0.75 | 1.00 | 0.50 |

## Сравнение с базовым прогоном

Парный бутстрап по кейсам, которые прошли оба прогона: два отдельных числа — не
сравнение, сравнивать надо один и тот же набор после пересэмплирования.

| метрика | текущий | базовый | дельта | 95% ДИ | p(дельта <= 0) | n |
|---|---|---|---|---|---|---|
| `recall` | 0.993 | 0.993 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `context_recall` | 1.000 | 0.996 | +0.004 | [+0.000, +0.011] | 0.365 | 137 (-) |
| `rr` | 0.850 | 0.849 | +0.001 | [+0.000, +0.004] | 0.355 | 137 (-) |
| `citation_supported` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `escalation_correct` | 0.942 | 0.934 | +0.007 | [-0.044, +0.058] | 0.421 | 137 (-) |
| `escalation_matched` | 0.949 | 0.942 | +0.007 | [-0.044, +0.058] | 0.421 | 137 (-) |
| `contains_expected` | 0.912 | 0.891 | +0.022 | [-0.036, +0.080] | 0.260 | 137 (-) |
| `forbidden_clean` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |


Кейсы по одному — в артефакте `2026-10-24-eval-full-baseline-v5.jsonl` рядом с этим файлом.
