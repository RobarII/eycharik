# 0003: Hybrid retrieval, rerank, then generate

Status: accepted. Date: 2026-10-23.

## Context

Company questions are full of exact names: "ДМС", "ПОЛИПЛАСТИК", "1С:ЗУП", document numbers.
Dense vectors are weak on rare tokens and acronyms; lexical search is weak on paraphrases
("сколько дней отдыха" vs "отпуск"). Both failures are silent: the model answers from a plausible
but wrong chunk.

## Decision

Three stages, each measurable on its own:

1. Filter by audience and validity in SQL.
2. Retrieve `top 30` by cosine and `top 30` by `ts_rank` with the Russian dictionary, fuse with
   reciprocal rank fusion.
3. Rerank the fused list with a cross-encoder, keep `top 5`.

## Consequences

- Two indexes per chunk: `vector(1024)` and `tsvector`.
- Fusion and ranking selection live in `core/ranking.py` and are tested without a database.
- More CPU per question; the reranker runs locally and costs no tokens.
- Recall@5 becomes a number we can regress on, which pure vector search does not give us.

## Alternatives

Vector-only — rejected: fails on acronyms and identifiers. BM25-only — rejected: fails on
paraphrase. LLM query rewriting — deferred: it adds latency and cost before we have measured the
baseline.
