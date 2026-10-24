---
title: "Оценка 2026-10-23: tsrank-16"
summary: "16 кейсов, гейты пройдены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-23 — пройдена

- команда: `python -m onboarding.evals --retrieval-only --write --label tsrank-16`
- коммит: `b364fc8`
- модель: `n/a`
- окружение: `local`
- провайдер эмбеддингов: `openai`
- поиск: `openai/baai/bge-m3 + rerank:cohere/rerank-v3.5`
- кейсов: 16
- сгенерированные ответы: False

| метрика | значение | гейт |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.90 |
| `mrr` | 1.000 | >= 0.75 |


Кейсы по одному — в артефакте `2026-10-23-eval-retrieval-tsrank-16.jsonl` рядом с этим файлом.
