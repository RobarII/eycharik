# 0025 — Demo models: OpenCode Go answers, OpenRouter embeddings

Date: 2026-10-24
Status: accepted
Supersedes: the model choice in 0010 for this demo deployment, not the port design.

## Context

The demo host has no GigaChat key. It does reach two OpenAI-compatible gateways: OpenCode Go at
`https://opencode.ai/inference/go/v1` and OpenRouter at `https://openrouter.ai/api/v1`. Both
answered `200` from the host on 2026-10-24. The repository already has measured profiles for the
answer model `opencode-deepseek-v4.1-flash` and the embedder
`openrouter-qwen3-embedding-8b`; no new adapter is needed.

The host is in the Netherlands. That already makes the demo unsuitable for real personal data under
152-ФЗ, independent of the model vendor.

## Decision

The demo `.env.prod` uses:

- answer: `LLM_PROVIDER=openai`, `LLM_PROFILE=opencode-deepseek-v4.1-flash`,
  `LLM_BASE_URL=https://opencode.ai/inference/go/v1`, with the OpenCode Go session headers;
- embeddings: `EMBED_PROVIDER=openai`, `EMBED_PROFILE=openrouter-qwen3-embedding-8b`,
  `EMBED_BASE_URL=https://openrouter.ai/api/v1`, `EMBED_DIM=1024`.

The models are hosted APIs. The VPS stores no weights, needs no GPU, and downloads no model files.
Keys live only in `/opt/onboarding/.env.prod`.

GigaChat remains the single-vendor alternative for a Russian-hosted pilot: switch the commented
block in `.env.production.example`, reindex the corpus with the GigaChat embedder, and run the evals.
That switch is a deployment change, not a code change.

## Consequences

- The demo uses two vendors and two keys: `LLM_API_KEY` for OpenCode Go and `EMBED_API_KEY` for
  OpenRouter. A failure in either degrades the same way as before: answers escalate, retrieval
  falls back to its hybrid order.
- The embedding width stays 1024. A different embedder width is a migration plus a reindex, never a
  setting.
- This does not satisfy 152-ФЗ localisation. The demo carries synthetic or public data only.
- The production guard still rejects `LLM_PROVIDER=extractive` and `EMBED_PROVIDER=hashing`.

## Alternatives

- GigaChat for both roles — the right choice for a Russian pilot, but it needs a Sber key that this
  demo does not have.
- Local weights on the VPS — rejected: one vCPU and 921 MiB of RAM cannot serve an answer model and
  an embedder, and the host has no GPU.
