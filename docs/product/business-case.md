# Business case: onboarding assistant, Russian-hosted pilot

Status: draft for the client. Every number is either measured in this repository, read from a vendor
price list on 2026-10-25, or explicitly marked **assumption** with the party that must confirm it.
Nothing here is a promise of quality; the quality gates live in [evals](../evals/README.md).

## The decision this document supports

One vendor, Russian-hosted, three calls per answer (chat, embeddings, rerank). Managed API costs
**≈ 0.032 ₽ per answer**; a self-hosted GPU costs the same per answer at the margin but **71 456 ₽
per month** before the first question. For onboarding volumes the managed option wins by two orders
of magnitude, so a GPU is justified by data locality or latency, not by cost.

## Inputs

| Input | Value | Type | Source |
|---|---|---|---|
| Input tokens per answer | 2 208 | measured | [token budget](../measurements/2026-10-25-token-budget.md) |
| Completion tokens per answer | 250 typical, 700 cap | budget | profile limit, not a measurement |
| Chat + embed + rerank price | 0.030 + 0.00002 + 0.0017 ₽ | list price, 22% VAT | [vendor comparison](vendor-comparison.md) |
| Corpus reindex | 0.012 ₽ one-off | derived | 89 chunks × 226 tokens, `bge-m3` |
| Full eval run | ≈ 4 ₽ | derived | 137 cases × 2 458 tokens |
| Answers per employee per month | 20 | **assumption** | client: onboarding bot usage |
| HR FTE loaded cost | 90 000 ₽/month | **assumption** | client's payroll |
| HR routine share | 40% | **client's own claim** | [case brief](../case/poliplastic-2026.md) |
| Routine work removed by the bot | 50% | **assumption** | must be measured in the pilot |

## Load scenarios

| Scenario | Employees | Answers/month | Peak day (≈2%) |
|---|---|---|---|
| Pilot | 100 | 2 000 | 40 |
| One plant | 1 000 | 20 000 | 400 |
| Company | 5 000 | 100 000 | 2 000 |

## Monthly cost

Managed, `GigaChat3-10B-A1.8B` + `bge-m3` + `bge-reranker-v2-m3`, prices with VAT:

| Scenario | Variable ₽/month | Per employee ₽/month |
|---|---|---|
| Pilot, 2 000 answers | 63 | 0.63 |
| Plant, 20 000 answers | 634 | 0.63 |
| Company, 100 000 answers | 3 170 | 0.63 |

Self-hosted, one L4 24 GB (VK Cloud, with VAT, accepted as the market anchor):

| Item | ₽/month | Note |
|---|---|---|
| GPU server | 71 456 | `GPU2-16-72-L4-1`, 30 days |
| Model weights | 0 | MIT / Apache-2.0 |
| Corpus reindex | 0 | local |
| Ops on-call | **quote** | 0.25–0.5 FTE, not priced here |
| Backup, monitoring, storage | **quote** | not in the vendor price list |

A GPU at company volume costs **71 456 ₽/month against 3 170 ₽/month** for the managed API: 22× more
expensive, and it still needs an owner.

## Break-even and payback

```
break_even_answers_per_month = GPU ₽/month ÷ managed ₽/answer
L4  24 GB: 71 456 ÷ 0.032 ≈ 2.2 million answers/month
L40S 48 GB: 173 479 ÷ 0.032 ≈ 5.4 million answers/month
```

A company of 5 000 employees produces 0.1 million answers/month — 22× below the break-even. The
managed API stays cheaper until the deployment serves roughly 11 000 employees at the assumption
above, or until the traffic is not onboarding at all.

Savings side, with the assumptions above (illustration, not a commitment):

```
routine_hours_saved = HR_FTE × 40% × 50%          → 0.2 FTE
saving_per_month    = 0.2 × 90 000 = 18 000 ₽
cost_per_month      = 634 ₽ at plant volume
ratio               = saving ÷ cost ≈ 28×
```

The ratio is dominated by the HR FTE assumption, not by the API price — which is why the pilot must
measure the routine share instead of arguing about it. The API price stops mattering above roughly
10 000 answers/month.

## Sensitivity

Base is 0.0316 ₽/answer. Numbers recomputed with the same price list:

| Change | ₽/answer | vs base |
|---|---|---|
| Completion at the 700-token cap | 0.0371 | +17% |
| Eight chunks instead of five | 0.0399 | +26% |
| Chunks at p95 size (299 tokens) | 0.0499 | +58% |
| Reranker on the pricier `Qwen3-Reranker-0.6B` | 0.0367 | +16% |
| Chat on `GigaChat 3 Pro` | 0.207 | ×6.5 |
| Chat on `DeepSeek V4 Flash` | 0.119 | ×3.8 |

Two conclusions hold under every row: the answer cost is small against one HR hour, and the chat
model is the only line that can move it. Reranking, embeddings and the corpus are noise.

## Costs the per-answer number hides

| Cost | Order | Owner |
|---|---|---|
| App host, Postgres, backups | quote, not captured | DevOps, from the invoice |
| Monitoring and on-call | quote | DevOps |
| 152-ФЗ paperwork: errand of processing, DPA, attestation review | legal hours | client's DPO |
| Model vendor change: new profile, reindex, eval run | ~1 day of work + 4 ₽ of tokens | engineer |
| Retention: storage of messages and audit rows | grows with `DATA_RETENTION_DAYS` | client policy |
| Price changes | vendor's right; the port makes the switch cheap | procurement |

## Risks and what reduces them

| Risk | Effect | Mitigation |
|---|---|---|
| Vendor raises prices 3× | 0.032 → 0.096 ₽/answer, still < 1% of one HR hour | the ports make a switch a settings change; the eval matrix is the cost |
| Vendor outage | answers escalate to a human (`reason: unavailable`) | second profile, no second implementation |
| Data leaves Russia | 152-ФЗ violation | managed RU internal-only models, or self-host |
| Embedder replaced | reindex + migration, not a setting | width stays 1024 unless a migration is planned |
| Latency regression | p95 gates fail before users notice | `make eval` with the gates in [evals](../evals/README.md) |
| Quality regression from a cheaper model | escalations rise, HR does the work anyway | golden set + escalation gates |

## Gates before a purchase order

1. `make eval` green on the candidate profile, with the measurement file.
2. Errand of processing under 152-ФЗ art. 6 part 3 signed, data localised per art. 18 part 5.
3. Written offer with currency, VAT, term, volume break, and price-change clause.
4. Written answer on training on our data: off.
5. Exit plan: who reindexes, how long, what the corpus re-embedding costs.

## What this document does not claim

- It does not claim the assistant saves 70% of HR work. That is the client's expectation in the
  brief; the pilot measures it.
- It does not price the app host, backups, or on-call: those are quotes, and a number invented here
  would be a lie with a decimal point.
- It does not compare answer quality between vendors; only [evals](../evals/README.md) do that.
