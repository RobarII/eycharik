---
title: "Оценка 2026-10-23: bge-m3-rerank"
summary: "12 кейсов, гейты провалены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-23 — провалена

- команда: `python -m onboarding.evals --write --label bge-m3-rerank`
- коммит: `37be26e`
- модель: `openai/deepseek-v4.1-flash @ https://opencode.ai/inference/go/v1`
- окружение: `local`
- провайдер эмбеддингов: `openai`
- кейсов: 12
- сгенерированные ответы: True

| метрика | значение | гейт |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.90 |
| `mrr` | 1.000 | >= 0.75 |
| `citation_support` | 1.000 | >= 1.00 |
| `escalation_correctness` | 1.000 | >= 0.90 |
| `answer_contains` | 1.000 | >= 1.00 |
| `p95_latency_ms` | 6008.000 | <= 3000.00 |
| `cost_per_answer_rub` | 0.000 |  |

Проваленные гейты: p95_latency_ms


Кейсы по одному — в артефакте `2026-10-23-eval-full-bge-m3-rerank.jsonl` рядом с этим файлом.
