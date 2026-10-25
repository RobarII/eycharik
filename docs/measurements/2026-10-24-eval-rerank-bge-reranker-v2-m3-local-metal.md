---
title: "Оценка 2026-10-24: дельта переранжирования bge-reranker-v2-m3 на Metal"
summary: "138 кейсов с ожидаемым документом: recall@5 0.978 -> 0.993, MRR 0.890 -> 0.973, порядок изменился на 136."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-24: дельта переранжирования

- команда: `python -m onboarding.evals.rerank --write --label bge-reranker-v2-m3-local-metal --note llama.cpp Q8_0 on Apple M2 Metal; per-call latency includes transport, one call per case`
- коммит: `bf10796`
- модель: `n/a`
- окружение: `local`
- поиск: `local-bge-m3 (bge-m3, dim 1024) + rerank:local-bge-reranker-v2-m3 (bge-reranker-v2-m3) + bm25:off + contextual:off`
- артефакт: `2026-10-24-eval-rerank-bge-reranker-v2-m3-local-metal.jsonl`
- заметка: llama.cpp Q8_0 on Apple M2 Metal; per-call latency includes transport, one call per case
- кейсов: 138
- сгенерированные ответы: False

Считаются только кейсы с ожидаемым документом: там, где ожидать нечего, ранга нет.

| метрика | до реранка | после |
|---|---|---|
| `recall@5` | 0.978 | 0.993 |
| `mrr` | 0.890 | 0.973 |

| счёт | значение |
|---|---|
| порядок изменился | 136 / 138 |
| отказов | 0 |
| латентность реранка, `p50` | 2674 мс |
| латентность реранка, `p95` | 4098 мс |

Гейта нет: реранкер — улучшение, а не зависимость (ADR 0008). Отказ оставляет
гибридный порядок, поэтому `mrr` до реранка и есть запасной вариант.
