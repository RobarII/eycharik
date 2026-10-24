---
title: "Оценка 2026-10-23: answer-v3-gpt-4.1-mini"
summary: "12 кейсов, гейты пройдены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-23 — пройдена

- команда: `python -m onboarding.evals --write --label answer-v3-gpt-4.1-mini --note prompt v3 forbids generic answers to personal questions`
- коммит: `6fc76ea`
- модель: `openai/openai/gpt-4.1-mini @ https://openrouter.ai/api/v1`
- окружение: `local`
- провайдер эмбеддингов: `openai`
- поиск: `openai/baai/bge-m3 + rerank:cohere/rerank-v3.5`
- заметка: промпт v3 запрещает общие ответы на личные вопросы
- кейсов: 12
- сгенерированные ответы: True

| метрика | значение | гейт |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.90 |
| `mrr` | 1.000 | >= 0.75 |
| `citation_support` | 1.000 | >= 1.00 |
| `escalation_correctness` | 1.000 | >= 0.90 |
| `answer_contains` | 1.000 | >= 1.00 |
| `p95_latency_ms` | 2343.000 | <= 8000.00 |
| `cost_per_answer_rub` | 0.070 |  |


Кейсы по одному — в артефакте `2026-10-23-eval-full-answer-v3-gpt-4.1-mini.jsonl` рядом с этим файлом.
