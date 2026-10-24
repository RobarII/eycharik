---
title: "Оценка 2026-10-24: prompt-v6-subset"
summary: "20 кейсов, гейты провалены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-24 — провалена

- команда: `python -m onboarding.evals --write --only it-equipment-request,commercial-secret-scope,unpaid-leave-days,maternity-days,guest-wifi,personal-data-third-parties,qc-stages,counterparty-check-term,repair-loaner,training-budget-size,probation-extension-length,sales-contract-blocked,overtime-pay,quality-deviation,dms-family,phishing-drill,ecology-polymer-waste,it-runbook-blocked,hr-only-sick-leave,salary-bands-blocked --label prompt-v6-subset --compare docs/measurements/2026-10-24-eval-full-baseline-v1.jsonl`
- коммит: `2fa84b7`
- модель: `openai/opencode-deepseek-v4.1-flash (deepseek-v4.1-flash) @ https://opencode.ai/inference/go/v1`
- окружение: `local`
- провайдер эмбеддингов: `openai`
- поиск: `openrouter-qwen3-embedding-8b (qwen/qwen3-embedding-8b, dim 1024) + rerank:openrouter-nemotron-rerank-8b (nvidia/nemotron-3.5-rerank-8b:free) + bm25:off + contextual:off`
- артефакт: `2026-10-24-eval-full-prompt-v6-subset.jsonl`
- кейсов: 20
- сгенерированные ответы: True

| метрика | значение | гейт |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.90 |
| `mrr` | 0.896 | >= 0.75 |
| `leak_rate` | 0.000 | <= 0.00 |
| `context_recall_at_5` | 1.000 | >= 0.90 |
| `context_fragment_coverage` | 0.938 | >= 0.98 |
| `p95_completion_ms` | 10388.000 | <= 8000.00 |
| `p95_answer_ms` | 12970.000 | <= 15000.00 |
| `citation_support` | 1.000 | >= 1.00 |
| `escalation_correctness` | 1.000 | >= 0.90 |
| `escalation_recall` | 1.000 | >= 0.90 |
| `escalation_precision` | 1.000 | >= 0.90 |
| `reason_accuracy` | 1.000 | >= 0.90 |
| `answer_contains` | 0.938 | >= 1.00 |
| `cost_completion_rub` | 0.086 |  |

Проваленные гейты: context_fragment_coverage, answer_contains, p95_completion_ms

## Страты

Одна сводка скрывает сломавшуюся страту. Гейт приводится по страте, только если
в ней не меньше десяти кейсов.

| страта | кейсов | recall@5 | context@5 | mrr | эскалация | contains |
|---|---|---|---|---|---|---|
| `fact` | 16 | 1.00 | 1.00 | 0.90 | 1.00 | 0.94 |
| `acl` | 4 | 0.00 | - | 0.00 | 1.00 | - |

## Сравнение с базовым прогоном

Парный бутстрап по кейсам, которые прошли оба прогона: два отдельных числа — не
сравнение, сравнивать надо один и тот же набор после пересэмплирования.

| метрика | текущий | базовый | дельта | 95% ДИ | p(дельта <= 0) | n |
|---|---|---|---|---|---|---|
| `recall` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 20 (-) |
| `context_recall` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 20 (-) |
| `rr` | 0.717 | 0.717 | +0.000 | [+0.000, +0.000] | 1.000 | 20 (-) |
| `citation_supported` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 20 (-) |
| `escalation_correct` | 1.000 | 0.600 | +0.400 | [+0.200, +0.600] | 0.000 | 20 (-) |
| `escalation_matched` | 1.000 | 0.700 | +0.300 | [+0.100, +0.500] | 0.001 | 20 (-) |
| `contains_expected` | 0.950 | 0.750 | +0.200 | [+0.050, +0.400] | 0.013 | 20 (-) |
| `forbidden_clean` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 20 (-) |


Кейсы по одному — в артефакте `2026-10-24-eval-full-prompt-v6-subset.jsonl` рядом с этим файлом.
