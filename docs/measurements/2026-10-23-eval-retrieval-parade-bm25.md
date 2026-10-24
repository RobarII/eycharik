---
title: "Оценка 2026-10-23: parade-bm25"
summary: "16 кейсов, гейты пройдены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-23 — пройдена

- команда: `python -m onboarding.evals --retrieval-only --write --label parade-bm25`
- коммит: `b364fc8`
- модель: `n/a`
- окружение: `local`
- провайдер эмбеддингов: `openai`
- поиск: `openai/baai/bge-m3 + rerank:cohere/rerank-v3.5`
- кейсов: 16
- сгенерированные ответы: False
- проверка: branch `experiment/bm25` (commit `d54287d`), ParadeDB sidecar on port 5433
- результат: MRR 0.938 vs 1.000 without BM25; see [ADR 0012](../decisions/0012-no-bm25-in-request-path.md)

| метрика | значение | гейт |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.90 |
| `mrr` | 0.938 | >= 0.75 |


Кейсы по одному — в артефакте `2026-10-23-eval-retrieval-parade-bm25.jsonl` рядом с этим файлом.
