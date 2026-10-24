---
title: "Оценка 2026-10-23: qwen3-embedding-8b"
summary: "132 кейсов, гейты пройдены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-23 — пройдена

- команда: `python -m onboarding.evals --retrieval-only --write --label qwen3-embedding-8b`
- коммит: `eb70b76`
- модель: `n/a`
- окружение: `local`
- провайдер эмбеддингов: `openai`
- поиск: `openrouter-qwen3-embedding-8b (qwen/qwen3-embedding-8b, dim 1024) + rerank:openrouter-nemotron-rerank-8b (nvidia/nemotron-3.5-rerank-8b:free)`
- кейсов: 132
- сгенерированные ответы: False

| метрика | значение | гейт |
|---|---|---|
| `recall_at_5` | 0.992 | >= 0.90 |
| `mrr` | 0.951 | >= 0.75 |
| `leak_rate` | 0.000 | <= 0.00 |


Кейсы по одному — в артефакте `2026-10-23-eval-retrieval-qwen3-embedding-8b.jsonl` рядом с этим файлом.
