# Vendor comparison for a Russian-hosted pilot

Prices read on **2026-10-25**. Every line carries its source, its currency, its VAT treatment and
whether it is a list price or a quote. A price without those four is a rumour.

Token counts come from [2026-10-25-token-budget.md](../measurements/2026-10-25-token-budget.md):
**2 208 input + 250 completion tokens per answer**, reranker sees 30 candidates ≈ 6 800 tokens.

## How to read the table

- `chat ₽/answer` = `(2208 × in + 250 × out) / 1e6`, VAT included where the source includes it.
- `rerank ₽/answer` = `6800 × rerank price / 1e6`.
- Anything marked **quote** is not a list price: it needs a signed offer before it enters a business
  case. Ask for it in writing, with the term and the volume break.

## Managed model APIs

Cloud.ru Foundation Models, tariff appendix №7.EVO.11.2, prices **with 22% VAT**
([source](https://cdn.cloud.ru/docs/legal/tariffs/evolution/current-version/foundation-models.pdf)):

| Model | In, ₽/1M | Out, ₽/1M | ₽/answer | Note |
|---|---|---|---|---|
| `GigaChat3-10B-A1.8B` | 12.20 | 12.20 | **0.030** | internal, 262k context, MIT weights upstream |
| `gpt-oss-120b` | 15.86 | 61.00 | 0.050 | internal, Apache-2.0 upstream, RU quality unmeasured |
| `DeepSeek V4 Flash` | 43.30 | 86.58 | 0.117 | internal |
| `GigaChat 3 Pro` | 73.03 | 176.39 | 0.205 | internal |
| `GigaChat Ultra` | 96.22 | 288.60 | 0.285 | internal |
| `GigaChat-2-Max` | 569.34 | 569.34 | 1.399 | internal, legacy price level |

| Component | ₽/1M | ₽/answer | Note |
|---|---|---|---|
| `bge-m3` embeddings | 0.61 | ≈ 0.00002 (query only) | 1024 dims, matches the column |
| `Qwen3-Embedding-0.6B` | 0.854 | ≈ 0.00003 | 1024 dims |
| `GigaEmbedding-0.5B` | 3.32 | ≈ 0.0001 | 1024 dims, MIT |
| `GigaEmbedding-3B` | 32.22 | ≈ 0.001 | 2048 dims, migration + reindex |
| `bge-reranker-v2-m3` | 0.244 | **0.0017** | 30 candidates |
| `Qwen3-Reranker-0.6B` | 0.854 | 0.006 | 30 candidates |
| `DeepSeek-OCR-2` in / out | 54.90 / 61.00 | — | only if `doc-scan` were replaced |

Corpus reindex is one-off: 0.012 ₽ with `bge-m3`, 0.65 ₽ with `GigaEmbedding-3B`.

**Best single vendor:** `GigaChat3-10B-A1.8B` + `bge-m3` + `bge-reranker-v2-m3` ≈ **0.032 ₽/answer**.

Selectel Token Factory, list prices **VAT treatment not stated on the page**, product in public
preview ([source](https://selectel.ru/services/cloud/token-factory/)):

| Model | In, ₽/1M | Out, ₽/1M | ₽/answer |
|---|---|---|---|
| `Qwen-3.8-Flash-Next` | 20.85 | 61.30 | 0.063 |
| `GLM-5.3-flash` | 74.64 | 248.55 | 0.229 |
| `DeepSeek-V4-Flash` | 75.42 | 186.29 | 0.215 |
| `Qwen-3.8-27B` | 31.01 | 206.50 | 0.121 |
| `Kimi-K2.7-Code` | 157.20 | 628.70 | 0.506 |

No embeddings or rerank in the published catalogue, and the ToS excludes personal-data processing
from Selectel's responsibility. Not a single-vendor pilot option; usable as a second vendor for
non-personal traffic.

Sber GigaChat packages, prices **with VAT**, valid for existing `ООО «СалютДевайсы»` clients; since
2026-09-01 new clients buy the same models through cloud.ru
([source](https://developers.sber.ru/docs/ru/gigachat/tariffs/legal-tariffs)):

| Package | ₽ per 1M tokens | ₽/answer | Note |
|---|---|---|---|
| GigaChat Lite, 300M | 65.00 | 0.160 | prepaid, 1 month validity |
| GigaChat Pro, 50M | 500.00 | 1.231 | prepaid |
| GigaChat Max, 30M | 650.00 | 1.599 | prepaid |
| Embeddings, 1B | 14.00 | — | prepaid |

Pay-as-you-go minimum is 600 ₽/month. The packages are 5–8× the cloud.ru per-token price for the
same family, because a package is bought up front and expires monthly.

Yandex Cloud AI Studio: token price **not captured** on 2026-10-25 — the pricing page answers with
an anti-bot check. Treat Yandex as *quote pending*; its GPU rates are captured below.

MTS AI Cotype / MWS: no public price list, **quote only**. Just AI Caila: no public price list,
**quote only**. VK Cloud: no managed LLM API at all.

## GPU rental (self-hosted vLLM)

VK Cloud virtual servers, prices **with VAT**, per 30 days
([source](https://cloud.vk.ru/pricelist/)):

| Flavour | ₽/30 days | ₽/hour | Fits |
|---|---|---|---|
| `GPU2-16-72-L4-1` (L4 24 GB) | 71 456 | 99.2 | Lightning FP8 + 480M embedder + 0.6B reranker |
| `GPU3-16-112-L40S-1` (L40S 48 GB) | 173 479 | 241.0 | same, with headroom for 3B embedder |
| `GPU3-32-192-A100x80-1` (A100 80 GB) | 241 662 | 335.6 | 30B-class dense |
| `GPU-44-256-H200-1` (H200 141 GB) | 793 000 | 1 101.4 | 122B MoE FP8 |

Yandex Cloud DataSphere GPU rates, **with VAT**, per hour
([source](https://yandex.cloud/ru/docs/datasphere/pricing)):

| Flavour | ₽/hour | ₽/30 days |
|---|---|---|
| `gt4.1` (T4 16 GB) | 168.48 | 121 306 |
| `gt4i.1` (T4i 16 GB) | 234.00 | 168 480 |
| `g2.1` (A100 40 GB) | 542.88 | 390 874 |

Selectel GPU and MWS GPU: **quote only** — public pages are JavaScript-driven or absent; ask for a
written offer with the term and the model of the card. Cloud.ru ML Inference: **quote only** in the
same way; the Foundation Models token tariff above is the part that is published.

## The comparison that matters

| Option | ₽/answer | Fixed ₽/month | When it wins |
|---|---|---|---|
| Managed RU API (GigaChat3-10B + bge) | 0.032 | ≈ 0 | up to ~2.2M answers/month |
| One L4 24 GB, self-hosted | ≈ 0 marginal | 71 456 | above ~2.2M answers/month, or when no vendor may see the data |
| One L40S 48 GB, self-hosted | ≈ 0 marginal | 173 479 | above ~5.5M answers/month |

Break-even = `GPU ₽/month ÷ managed ₽/answer`. On onboarding traffic (2 000–100 000 answers/month,
see [business-case.md](../product/business-case.md)) the managed option is 35–1 100× cheaper, so the
GPU is bought for a reason other than money: a closed contour, a model that no vendor offers, or a
latency floor.

## What this table cannot tell you

- **Quality.** Vendor MTEB or vendor benchmarks are not our golden set; the RU dialogue quality of
  every candidate still needs `make eval` against `docs/evals/golden.yaml`.
- **Latency.** The p95 gates in `docs/evals/` are the contract; a cheaper model that misses
  `p95_answer_ms ≤ 15000` is not cheaper, it escalates.
- **Availability.** A single vendor is a single failure mode. Ports allow a second one, the eval
  matrix does not — that trade-off is in [0010](../decisions/0010-one-model-vendor.md).
