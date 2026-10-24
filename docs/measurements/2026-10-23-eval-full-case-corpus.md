---
title: "Оценка 2026-10-23: прогон полный case corpus"
summary: "16 кейсов, гейты пройдены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-23 — пройдена

- команда: `python -m onboarding.evals --write`
- коммит: `8ba530d`
- модель: `openai/openai/gpt-4.1-mini @ https://openrouter.ai/api/v1`
- окружение: `local`
- провайдер эмбеддингов: `openai`
- поиск: `openai/baai/bge-m3 + rerank:cohere/rerank-v3.5`
- кейсов: 16 (12 general + 4 on the client's own documents: anti-corruption, commercial secret)
- сгенерированные ответы: True

| метрика | значение | гейт |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.90 |
| `mrr` | 1.000 | >= 0.75 |
| `citation_support` | 1.000 | >= 1.00 |
| `escalation_correctness` | 1.000 | >= 0.90 |
| `answer_contains` | 1.000 | >= 1.00 |
| `p95_latency_ms` | 2237.000 | <= 8000.00 |
| `cost_per_answer_rub` | 0.077 |  |


Кейсы по одному — в артефакте `2026-10-23-eval-full-case-corpus.jsonl` рядом с этим файлом.
