# Vendor comparison for a Russian-hosted pilot

This file is the **single home for prices** in the repository. Another document either links here or
quotes a number as `quoted from vendor-comparison`; a price that drifts into a third place is how a
business case fails diligence.

Prices read on **2026-10-25**. Every line carries a source, a currency, a VAT treatment and a
confidence class. A price without those four is a rumour, and a rumour in a business case becomes a
lost argument in a procurement meeting.

## Confidence classes

| Class | Meaning | What it is worth |
|---|---|---|
| **A** | public list price on the vendor's own site or tariff PDF | good until the next price change; ask for the validity term |
| **B** | price from a contract appendix (`ПРИЛОЖЕНИЕ №…` to a договор) | valid for that contract; a new client may get different numbers |
| **C** | no public price; written offer required | cannot enter a business case until the offer exists |

## Token budget per tokenizer

One measurement cannot price five models: every vendor bills its own tokenizer, and the same prompt
costs 1 078 to 1 316 tokens depending on the model. The table below is the
[token budget measurement](../measurements/2026-10-25-token-budget.md), not an assumption.

| Model family | Prompt | Chunk | Input (5 chunks) | Completion (700 chars) |
|---|---|---|---|---|
| GigaChat 3.x | 1 078 | 226 | 2 208 | 175 |
| T-lite | 1 078 | 231 | 2 233 | 171 |
| Qwen 3.5 | 1 211 | 261 | 2 516 | 178 |
| GLM 5.3 | 1 211 | 256 | 2 491 | 170 |
| DeepSeek V4 | 1 316 | 282 | 2 726 | 177 |
| gpt-oss | 1 196 | 251 | 2 451 | 169 |
| Reranker, 30 candidates | — | — | 6 272 | — |

The spread between the cheapest and the most expensive tokenizer is 23%, which is larger than most
differences between vendor discounts. Pricing a Qwen model with the GigaChat budget would understate
it by 14%.

## Managed model APIs, per answer

Formula: `in × price_in / 1e6 + out × price_out / 1e6 + rerank`. Rerank is `6 272 × 0.244 / 1e6 =
0.0015 ₽` for `bge-reranker-v2-m3` on every row.

Cloud.ru Foundation Models — class **B**, prices **with 22% VAT**, source: tariff appendix
№7.EVO.11.2 ([PDF](https://cdn.cloud.ru/docs/legal/tariffs/evolution/current-version/foundation-models.pdf)).
The caveat matters: an appendix to a договор is not a public offer, and a new client is quoted from
the current cloud.ru catalogue instead.

| Model | In, ₽/1M | Out, ₽/1M | Chat ₽ | Total ₽ |
|---|---|---|---|---|
| `GigaChat3-10B-A1.8B` | 12.20 | 12.20 | 0.0291 | **0.0306** |
| `gpt-oss-120b` | 15.86 | 61.00 | 0.0492 | 0.0507 |
| `DeepSeek V4 Flash` | 43.30 | 86.58 | 0.1334 | 0.1349 |
| `GigaChat 3 Pro` | 73.03 | 176.39 | 0.1921 | 0.1936 |
| `GigaChat Ultra` | 96.22 | 288.60 | 0.2630 | 0.2645 |
| `GigaChat-2-Max` | 569.34 | 569.34 | 1.3567 | 1.3583 |

Selectel Token Factory — class **A** with an unresolved VAT question (`НДС` is not stated on the
page), product in public preview ([source](https://selectel.ru/services/cloud/token-factory/)):

| Model | In, ₽/1M | Out, ₽/1M | Total ₽ |
|---|---|---|---|
| `Qwen-3.8-Flash-Next` | 20.85 | 61.30 | 0.0649 |
| `Qwen-3.8-27B` | 31.01 | 206.50 | 0.1163 |
| `GLM-5.3-flash` | 74.64 | 248.55 | 0.2297 |
| `DeepSeek-V4-Flash` | 75.42 | 186.29 | 0.2401 |
| `Kimi-K2.7-Code` | 157.20 | 628.70 | not measured: no tokenizer |

Sber GigaChat packages — class **A**, prices **with VAT**, for existing `ООО «СалютДевайсы»`
clients; since 2026-09-01 new clients buy through cloud.ru
([source](https://developers.sber.ru/docs/ru/gigachat/tariffs/legal-tariffs)):

| Package | ₽/1M | Total ₽ | Note |
|---|---|---|---|
| Lite, 300M | 65.00 | 0.1564 | prepaid, expires in 1 month |
| Pro, 50M | 500.00 | 1.1930 | prepaid |
| Max, 30M | 650.00 | 1.5505 | prepaid |

Pay-as-you-go minimum 600 ₽/month. Prepaid packages are 5–8× the cloud.ru per-token price for the
same model family, because the volume expires monthly.

## Embeddings, rerank, OCR

| Component | ₽/1M tokens | Per answer | Class |
|---|---|---|---|
| `bge-m3` (1024 dims) | 0.61 | 0.000007 (11-token query) | B |
| `Qwen3-Embedding-0.6B` (1024) | 0.854 | 0.000009 | B |
| `GigaEmbedding-0.5B` (1024) | 3.32 | 0.00004 | B |
| `GigaEmbedding-3B` (2048, migration + reindex) | 32.22 | 0.00035 | B |
| `bge-reranker-v2-m3` (30 candidates) | 0.244 | 0.0015 | B |
| `Qwen3-Reranker-0.6B` (30 candidates) | 0.854 | 0.0054 | B |
| `DeepSeek-OCR-2` in / out | 54.90 / 61.00 | — | B |

Corpus reindex is one-off: 20 785 tokens, i.e. 0.013 ₽ with `bge-m3` and 0.67 ₽ with
`GigaEmbedding-3B`. Reindexing is never a budget line; it is a migration task.

## What is still missing (class C)

| Vendor / item | Why it is missing |
|---|---|
| Yandex Cloud AI Studio token prices | pricing page answers with an anti-bot check; request an offer |
| Selectel GPU servers | public page is JavaScript-driven; price lives in the panel or in an offer |
| Cloud.ru ML Inference GPU | not in the Foundation Models tariff appendix |
| MWS / MTS AI Cotype | no public price list; on-prem, quoted per project |
| Just AI Caila | no public price list |
| Kimi K2.7 tokenizer | not fetched; cost row unmeasurable until it is |
| VAT for Selectel Token Factory | not stated on the page; ask before comparing |

A comparison with six class-C holes is a shortlist, not a decision. The business case says so
explicitly.

## GPU rental (self-hosted vLLM)

VK Cloud, class **A**, prices **with VAT**, per 30 days
([source](https://cloud.vk.ru/pricelist/)):

| Flavour | ₽/30 days | ₽/hour | Card |
|---|---|---|---|
| `GPU2-16-72-L4-1` | 71 456 | 99.2 | L4 24 GB |
| `GPU3-16-112-L40S-1` | 173 479 | 241.0 | L40S 48 GB |
| `GPU3-32-192-A100x80-1` | 241 662 | 335.6 | A100 80 GB |
| `GPU-44-256-H200-1` | 793 000 | 1 101.4 | H200 141 GB |

Yandex Cloud DataSphere, class **A**, **with VAT**, per hour
([source](https://yandex.cloud/ru/docs/datasphere/pricing)):

| Flavour | ₽/hour | ₽/30 days |
|---|---|---|
| `gt4.1` T4 16 GB | 168.48 | 121 306 |
| `gt4i.1` T4i 16 GB | 234.00 | 168 480 |
| `g2.1` A100 40 GB | 542.88 | 390 874 |

A GPU price is not yet a `₽/answer`: throughput on a given card is unmeasured in this repository.
Until a load test exists, the GPU side of the comparison is a **fixed monthly cost**, not a unit
cost, and any break-even built on "≈ 0 marginal" is arithmetic, not evidence.

## The one comparison this file supports

| Option | Per answer | Fixed ₽/month | Confidence |
|---|---|---|---|
| Managed RU API (`GigaChat3-10B` + `bge-m3` + `bge-reranker-v2-m3`) | 0.0306 | ≈ 0 | B |
| One L4 24 GB, self-hosted | not measurable yet | 71 456 | A |
| One L40S 48 GB, self-hosted | not measurable yet | 173 479 | A |

Break-even arithmetic, with the caveat above:
`71 456 ÷ 0.0306 ≈ 2.3 million answers/month` for the L4, `5.7 million` for the L40S. Treat it as a
sanity check on scale, not as a recommendation.

## What this file cannot tell you

- **Answer quality.** Vendor benchmarks and MTEB scores are not our golden set; only
  [evals](../evals/README.md) decide, per candidate profile, with a measurement file.
- **Latency.** The gates are `p95_completion_ms ≤ 8000` and `p95_answer_ms ≤ 15000`; a cheaper model
  that misses them is not cheaper, it escalates.
- **Availability.** One vendor is one failure mode; the ports allow a second, the eval matrix does
  not ([0010](../decisions/0010-one-model-vendor.md)).
- **Price stability.** No vendor on this list publishes a price validity term. Ask for it in writing;
  a 90-day price lock is worth more than a 3% discount.
