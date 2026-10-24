---
title: "Оценка 2026-10-23: gpt-4.1-mini-bge-m3-rerank"
summary: "12 кейсов, гейты пройдены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-23 — пройдена

- команда: `python -m onboarding.evals --write --label gpt-4.1-mini-bge-m3-rerank --note model swap to a stable provider; same retrieval stack`
- коммит: `6fc76ea`
- модель: `openai/openai/gpt-4.1-mini @ https://openrouter.ai/api/v1`
- окружение: `local`
- провайдер эмбеддингов: `openai`
- поиск: `openai/baai/bge-m3 + rerank:cohere/rerank-v3.5`
- заметка: смена модели на стабильного провайдера; стек поиска тот же
- кейсов: 12
- сгенерированные ответы: True

| метрика | значение | гейт |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.90 |
| `mrr` | 1.000 | >= 0.75 |
| `citation_support` | 1.000 | >= 1.00 |
| `escalation_correctness` | 0.917 | >= 0.90 |
| `answer_contains` | 1.000 | >= 1.00 |
| `p95_latency_ms` | 2236.000 | <= 8000.00 |
| `cost_per_answer_rub` | 0.067 |  |


Кейсы по одному — в артефакте `2026-10-23-eval-full-gpt-4.1-mini-bge-m3-rerank.jsonl` рядом с этим файлом.
