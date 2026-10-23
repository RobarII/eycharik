# 0009: An eight-second p95 budget for a hosted model

Status: accepted. Date: 2026-10-23. Supersedes the 3-second target in `docs/architecture.md`.

## Context

The first eval gate said p95 ≤ 3000 ms. It was written while the only provider was the offline
extractive demo, which reports zero latency by construction: the gate had never met a real model.

Measured on 2026-10-23, commit `56d2d9c`, twelve golden cases, local stack, `baai/bge-m3`
embeddings, `cohere/rerank-v3.5`:

| Pipeline | p95 |
|---|---|
| hybrid retrieval + `deepseek-v4.1-flash`, no rerank | 4615 ms |
| + reranker, five chunks in the prompt | 6008 ms |

The model call is 70–80 % of the time; the reranker is 0.7–1.6 s; retrieval is tens of
milliseconds. A 3-second budget cannot be met by any hosted model in this class, so the gate was
not measuring the product — it was measuring the demo.

## Decision

The end-to-end answer budget is **p95 ≤ 8000 ms**, measured by `make eval` with a real provider.

- The webhook budget stays strict: under 200 ms, unchanged (ADR 0002).
- The user sees a typing state while the answer is generated; eight seconds is inside what a
  messenger conversation tolerates for a substantive answer.
- The eval gate uses the same number as the runbook alert, so a regression fails a build before it
  pages anyone.
- If p95 crosses 8000 ms, the order of cuts is: `RERANK_LIMIT` 5 → 3, then `RECALL_LIMIT` 30 → 15,
  then a faster model. Each cut is a measurement, not a guess.

## Consequences

- The offline extractive eval still reports a latency of zero; it proves the contract, not the
  budget. Real-provider runs are the evidence.
- A provider incident can breach the budget without a code change. The circuit breaker (ADR 0007
  path) and the `llm-outage` runbook handle that case; the gate is about the code we ship.
- `docs/evals/README.md`, `docs/measurements/TEMPLATE.md`, and `evals/runner.py` carry the same
  number, and a test pins it.

## Alternatives

Keep 3000 ms and accept a red gate forever — rejected: a permanently failing gate teaches the team
to ignore gates. Measure the model only and exclude the reranker — rejected: the user waits for the
whole pipeline, not for a stage. Stream tokens to the user — deferred: MAX supports it, but the
answer contract validates citations before anything is sent.
