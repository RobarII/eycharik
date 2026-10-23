# 0008: Rerank through a hosted cross-encoder

Status: accepted. Date: 2026-10-23.

## Context

ADR 0003 fixed three retrieval stages: filter, hybrid recall, rerank. The third stage was missing:
the answerer took the fused list and cut it to `RERANK_LIMIT`. On the golden set that looked
harmless — recall@5 was already 1.0 — but the prompt still had to guess which of thirty candidates
was on point, and the order of the context was the order of the fusion.

Two constraints pushed the reranker out of the process:

- a local cross-encoder means a model file, a torch runtime, and a warm-up in every container;
- the deployment target is a small VM for a hackathon pilot, not a GPU box.

## Decision

Rerank through one HTTP call to a Cohere-shaped `/rerank` endpoint (Cohere, Jina, OpenRouter all
speak it). The stage is optional at configuration level:

- `RERANK_BASE_URL` empty → no reranker, the hybrid order stands;
- configured → `app/llm/rerank.py` sends the question and the fused candidates, keeps the returned
  order, and truncates to `RERANK_LIMIT`;
- any failure (timeout, 5xx, malformed body, duplicate or out-of-range index) raises
  `RerankUnavailableError`, the answerer records `rerank_failed`, and generation proceeds with the
  hybrid order. A reranker is an improvement, never a dependency.

The provider is `cohere/rerank-v3.5` through OpenRouter: 0.001 $ per search, multilingual, and it
returns a score that separates a relevant chunk from noise (0.63 vs 0.05 on a probe pair).

## Consequences

- One more network hop: measured 0.7–1.6 s for 5–30 documents.
- The reranker sees the question and the chunk text. It never sees more than the retrieval already
  permitted by the audience filter, so ACL evaluation stays in SQL and stays first.
- `recall@5` cannot regress from this stage; `mrr` can only improve, and on the golden set it went
  from 0.900 to 1.000.
- A reranker outage degrades quality, not availability.
- Cost is 0.001 $ per answered question, recorded in the measurement alongside the model cost.

## Alternatives

Local cross-encoder (bge-reranker, mmarco) — rejected for the pilot: a torch runtime and a model
download in every container for a 1 s saving. LLM-based listwise rerank — rejected: a second model
call with the same latency class as the answer itself. No reranker — rejected: the fused order put
the right chunk in the top five but not first, and `mrr` measures exactly that.
