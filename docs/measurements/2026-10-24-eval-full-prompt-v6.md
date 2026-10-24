---
title: "Оценка 2026-10-24: prompt-v6"
summary: "137 кейсов, гейты провалены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-24 — провалена

- команда: `python -m onboarding.evals --write --label prompt-v6 --note prompt v6 keeps the missing-fact test and separates it from wording --compare docs/measurements/2026-10-24-eval-full-baseline-v1.jsonl`
- коммит: `65fc273`
- модель: `openai/opencode-deepseek-v4.1-flash (deepseek-v4.1-flash) @ https://opencode.ai/inference/go/v1`
- окружение: `local`
- провайдер эмбеддингов: `openai`
- поиск: `openrouter-qwen3-embedding-8b (qwen/qwen3-embedding-8b, dim 1024) + rerank:openrouter-nemotron-rerank-8b (nvidia/nemotron-3.5-rerank-8b:free) + bm25:off + contextual:off`
- артефакт: `2026-10-24-eval-full-prompt-v6.jsonl`
- заметка: промпт v6 сохраняет проверку на отсутствующий факт и отделяет её от формулировки
- кейсов: 137
- сгенерированные ответы: True

| метрика | значение | гейт |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.90 |
| `mrr` | 0.941 | >= 0.75 |
| `leak_rate` | 0.000 | <= 0.00 |
| `context_recall_at_5` | 0.996 | >= 0.90 |
| `context_fragment_coverage` | 0.984 | >= 0.98 |
| `p95_completion_ms` | 9810.000 | <= 8000.00 |
| `p95_answer_ms` | 18378.000 | <= 15000.00 |
| `citation_support` | 1.000 | >= 1.00 |
| `escalation_correctness` | 0.956 | >= 0.90 |
| `escalation_recall` | 1.000 | >= 0.90 |
| `escalation_precision` | 0.750 | >= 0.90 |
| `reason_accuracy` | 0.917 | >= 0.90 |
| `answer_contains` | 0.918 | >= 1.00 |
| `answer_excludes` | 1.000 | >= 1.00 |
| `cost_completion_rub` | 0.081 |  |

Проваленные гейты: answer_contains, escalation_precision, p95_completion_ms, p95_answer_ms

## Страты

Одна сводка скрывает сломавшуюся страту. Гейт приводится по страте, только если
в ней не меньше десяти кейсов.

| страта | кейсов | recall@5 | context@5 | mrr | эскалация | contains |
|---|---|---|---|---|---|---|
| `fact` | 115 | 1.00 | 1.00 | 0.95 | 0.96 | 0.92 |
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
| `rr` | 0.845 | 0.841 | +0.004 | [+0.000, +0.011] | 0.362 | 137 (-) |
| `citation_supported` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |
| `escalation_correct` | 0.956 | 0.942 | +0.015 | [-0.036, +0.073] | 0.337 | 137 (-) |
| `escalation_matched` | 0.964 | 0.956 | +0.007 | [-0.036, +0.058] | 0.445 | 137 (-) |
| `contains_expected` | 0.927 | 0.942 | -0.015 | [-0.058, +0.036] | 0.775 | 137 (-) |
| `forbidden_clean` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 137 (-) |


Кейсы по одному — в артефакте `2026-10-24-eval-full-prompt-v6.jsonl` рядом с этим файлом.
