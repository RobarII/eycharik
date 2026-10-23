# 0010 — One vendor for answer, embeddings, and rerank

Date: 2026-10-23
Status: accepted

## Context

The pilot ran answers on a community gateway (`deepseek-v4.1-flash`) and retrieval on OpenRouter
(`baai/bge-m3` embeddings, `cohere/rerank-v3.5`). Two vendors meant two keys, two failure modes, and
two billing statements for one product.

The answer model was also unstable: with a 700-token cap, one in three calls returned HTTP 200 with
empty content — a reasoning model that spent its budget before writing an answer. The pipeline
correctly escalated those to a human (`reason: unavailable`), but a demo and an eval must not depend
on a coin flip.

Measured on 2026-10-23, same prompt, same five chunks, four calls each:

| model | empty answers | latency |
|---|---|---|
| `deepseek-v4.1-flash` (community gateway) | 3 / 8 | 2.1–4.8 s |
| `openai/gpt-4.1-mini` (OpenRouter) | 0 / 4 | 1.4–1.8 s |
| `openai/gpt-4o-mini` (OpenRouter) | 0 / 4 | 1.9–3.1 s |
| `deepseek/deepseek-chat-v3.1` (OpenRouter) | 0 / 4 | 6.1–17.0 s |
| `google/gemini-2.5-flash` (OpenRouter) | 0 / 4 | 0.2 s (error body) |

## Decision

One vendor: OpenRouter. One key in `LLM_API_KEY`, `EMBED_API_KEY`, `RERANK_API_KEY`.

- answer: `openai/gpt-4.1-mini`, temperature 0.2, 700 output tokens, JSON response format;
- embeddings: `baai/bge-m3`, 1024 dimensions;
- rerank: `cohere/rerank-v3.5`.

The answer request sets `response_format: json_object`; an empty completion is retried as a
transport failure (`EmptyCompletionError`) rather than reported to the employee.

## Consequences

- `cost_per_answer_rub` rose from 0.036 to 0.070 (≈ 0.7 ₽ per ten answers) and p95 fell from
  6603 ms to 2343 ms.
- Escalation correctness returned to 1.000; the previous model also needed prompt v3 to stop
  answering personal questions with general policy text.
- A single provider is a single point of failure. The ports stay provider-agnostic: `LLMProvider`
  already speaks the OpenAI chat-completions shape, so a second vendor is a settings change, not a
  rewrite. The offline extractive provider remains the no-network fallback for tests and demos.
- The key is per-environment and never enters git. Cost accounting reads
  `LLM_PRICE_INPUT_RUB_PER_1K` / `LLM_PRICE_OUTPUT_RUB_PER_1K`, so a price change is a config
  change, not a code change.

## Alternatives

- Keep the community gateway — rejected: empty completions are indistinguishable from a refusal
  unless every call is inspected, and the pilot cannot ship a coin flip.
- Local model — rejected for the pilot: GPU hosting is outside the client's infrastructure budget
  and the contract needs an answer in under eight seconds.
- Two vendors with automatic failover — deferred: the port allows it, but a fallback doubles the
  eval matrix and the pilot has one week.
