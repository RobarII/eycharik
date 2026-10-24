# 0026 — Russian-hosted model options for a 152-ФЗ pilot

Date: 2026-10-25
Status: proposed
Supersedes: the vendor choice in 0010 for a Russian-hosted deployment, not the port design.

## Context

The demo host sits in the Netherlands and the keys point at OpenCode Go and OpenRouter
([0025](0025-demo-models-on-opencode-and-openrouter.md)). That demo carries synthetic or public
data only. Real employee data needs the corpus and the prompts to stay inside Russia, an errand of
processing under 152-ФЗ art. 6 part 3, and a database localised per art. 18 part 5.

The ports are vendor-agnostic: `LLMProvider` speaks the OpenAI chat-completions shape, embeddings and
rerank are HTTP calls with a base URL. A vendor change is therefore a profile plus a key, and an
embedding width change is a migration plus a reindex.

Facts below were read from vendor documentation and model cards on 2026-10-25. None of them is our
measurement; a chosen vendor still needs an eval run and a measurement file.

## Options read on 2026-10-25

| Vendor | Chat | Embeddings | Rerank | Hosting / 152-ФЗ |
|---|---|---|---|---|
| Cloud.ru Foundation Models | GigaChat3-10B/3.5-432B, DeepSeek-V4-Pro, Qwen3.5, gpt-oss-120b | `BAAI/bge-m3`, Giga embeddings | `BAAI/bge-reranker-v2-m3` | OpenAI-compatible `/v1`; models split into internal (no data leaves, no logging) and external; Evolution AZ-1..3 holds an UZ-1 ISPDn attestation |
| Yandex Cloud / AI Studio | YandexGPT Pro/Lite | `text-search-doc` / `text-search-query` | none standalone | 152-ФЗ page claims 1119 + FSTEK 21 measures at UZ-1; an on-premises AI Studio delivery exists as a separate contract |
| Sber GigaChat API | GigaChat 2 Pro / Max | Embeddings (1024) | none public | `api.giga.chat`, Russian data centres; Enterprise with DPA/NDA and training on client data off by default |
| Selectel Token Factory | GLM, DeepSeek-V4-Flash, Qwen, Kimi | not listed | not listed | Russian data centres, no cross-border transfer, OpenAI-compatible; public preview; the ToS explicitly excludes personal-data processing from Selectel's responsibility |
| MTS AI Cotype / MWS | Cotype Pro | RAG module | — | on-prem only, OpenAI-compatible `/v1`, software registry entry 23756, MWS cloud has an attested 152-ФЗ segment |
| Just AI Caila | 300+ models | ? | ? | Russian legal entity, registry entry; catalogue mixes foreign models, so the route decides the law |
| VK Cloud | no managed LLM API | — | — | GPU infrastructure only |

Self-hosting on Russian GPU (Selectel, Cloud.ru ML Inference, VK Cloud, MWS) is the option with no
cross-border question at all: the model files and the prompts never leave the operator's contour.

## Decision (proposed)

Prices are in [vendor-comparison.md](../product/vendor-comparison.md); the money argument and the
scenarios are in [business-case.md](../product/business-case.md). One answer is 2 208 input and 250
completion tokens ([measurement](../measurements/2026-10-25-token-budget.md)), which prices the
recommended managed stack at **0.032 ₽/answer** against **71 456 ₽/month** for the smallest useful
GPU box.

Note one vendor fact: since 2026-09-01 new clients buy GigaChat models through cloud.ru rather than
through the Sber package list, so "GigaChat" and "Cloud.ru" are close to the same purchase.

For a Russian pilot, in preference order:

1. **Managed, least code:** Cloud.ru Foundation Models as one vendor for answer, embeddings and
   rerank — OpenAI-compatible `/v1`, internal models only, `BAAI/bge-m3` (1024) keeps the vector
   column, `bge-reranker-v2-m3` keeps the Cohere-shaped rerank call.
2. **Managed, GigaChat single vendor:** GigaChat 2 Pro plus GigaChat embeddings (1024), reranker
   disabled (`RERANK_BASE_URL=""`), hybrid order stands per [0008](0008-hosted-rerank.md).
3. **Own contour:** vLLM on Russian GPU with the shortlist in
   [model shortlist](#gpu-shortlist-read-2026-10-25) below.

The embedding width stays 1024 unless a migration and a reindex are part of the same change.

## GPU shortlist read 2026-10-25

Vendor-published numbers, not ours.

Embeddings (RU semantics first, column `MTEB (rus)` as published in the model card):

| Model | Dim | Params | License | MTEB (rus) |
|---|---|---|---|---|
| `ai-sage/Giga-Embeddings-instruct-480M-0826` | 1024 | 0.48B | MIT | 70.98 |
| `ai-sage/Giga-Embeddings-instruct-3B-0826` | 2048 | 3.15B | MIT | 74.57 |
| `ai-sage/Giga-Embeddings-instruct-10B-A1.8B-0826` | 1536 | 10.5B (1.8B active) | MIT | 74.99 |
| `ai-forever/FRIDA` | 1536 | 0.82B | — | 70.95 |
| `Qwen/Qwen3-Embedding-0.6B` | 1024 | 0.6B | Apache-2.0 | 63.64 |

The Giga embedders are instruction-style: `Instruct: {task}\nQuery: {text}` on the query only,
documents raw, mean pooling plus L2 normalisation. A local embedder therefore needs the query prefix
in configuration, not in the corpus.

Rerank: `BAAI/bge-reranker-v2-m3` (0.57B, Apache-2.0, 8192) is the default; `jinaai/jina-reranker-v3`
and `Qwen/Qwen3-Reranker-0.6B` / `-4B` are the alternatives. No RU-only reranker has comparable
adoption.

Answers, by GPU budget:

| Budget | Model | Params | License | Context |
|---|---|---|---|---|
| 1 × 24 GB | `ai-sage/GigaChat3.1-10B-A1.8B` (FP8) | 11.5B / 1.8B active | MIT | 262k |
| 1 × 24 GB | `t-tech/T-lite-it-2.1` | 8.2B | Apache-2.0 | 40k |
| 1 × 48 GB | `Qwen/Qwen3.5-9B` | 9.7B | Apache-2.0 | — |
| 2 × 80 GB | `Qwen/Qwen3.5-122B-A10B` (FP8) | 125B / 10B active | Apache-2.0 | — |
| 8 × 80 GB | `ai-sage/GigaChat3.5-432B-A28B` (FP8) | 434B / 28B active | MIT | — |

OCR already runs in-process: `doc-scan` uses PP-OCRv5 Cyrillic over ONNX Runtime and needs no GPU.

## Consequences

- One 24 GB GPU carries the whole pipeline: Lightning FP8 for answers, the 480M embedder, the
  0.57B reranker. The 3B and 10B embedders buy ~3.6–4 MTEB points for a migration to 1536/2048
  dimensions plus a reindex.
- Cloud.ru removes two vendors and two keys; it adds a ToS question — the attestation covers the
  cloud, not the model service, so the errand of processing must be signed for the service itself.
- Selectel Token Factory is not a candidate for personal data on its own ToS: its text disclaims
  personal-data processing. Dedicated Inference or a self-hosted vLLM on the same GPU fleet is.
- Every option needs its own measurement file before this ADR moves to `accepted`.
- Managed wins on money until roughly 2.2 million answers/month (one L4 break-even); a GPU is bought
  for a closed contour or a latency floor, not for cost.
- GigaChat packages are 5–8× the cloud.ru per-token price for the same family; prepaid packages
  expire monthly, so pay-as-you-go on cloud.ru is the cheaper path at pilot volume.

## Alternatives

- Stay on OpenRouter — rejected for real data: the host and the vendors are outside Russia.
- One vendor for everything including OCR — not needed: the OCR already runs locally on CPU.
