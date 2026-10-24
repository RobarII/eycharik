# Business case: onboarding assistant, Russian-hosted pilot

Status: draft for the client. Prices live in [vendor-comparison.md](vendor-comparison.md), token
counts in [the token budget measurement](../measurements/2026-10-25-token-budget.md). This document
does not restate either — it spends them.

Two rules this document follows:

1. **No invented numbers.** Where an input belongs to the client, the row says so and stays empty
   until the client fills it. An empty cell is cheaper than a wrong one.
2. **Arithmetic is not a recommendation.** A break-even is a division. Whether to buy the GPU is a
   decision with reasons that may have nothing to do with the division.

## The question this document answers

At onboarding volumes, does the assistant cost less than the HR time it removes — and does a
self-hosted GPU change that answer?

Short version: the model cost is small enough that the answer hinges on the HR inputs, not on the
vendor. The GPU is a decision about the contour, not about money.

## Inputs

| Input | Value | Type | Owner |
|---|---|---|---|
| Input tokens per answer, `GigaChat3-10B` tokenizer | 2 208 (5 chunks) | measured | repo |
| Completion, 700 Russian characters | 175 tokens | measured | repo |
| Profile output ceiling | 700 tokens | policy | repo (4× the measured answer) |
| Chat + embeddings + rerank | 0.0306 ₽/answer | list price, class B | [vendor-comparison](vendor-comparison.md) |
| One-off corpus reindex | 0.013 ₽ | derived | [vendor-comparison](vendor-comparison.md) |
| Answers per employee per month | **to be measured** | from MAX logs after two weeks | client |
| New employees per month | **to be supplied** | HR plan | client |
| HR FTE loaded cost | **to be supplied** | payroll | client |
| Share of HR time on routine questions | **to be measured** | the brief claims 40%, the pilot measures it | client + repo evals |
| Share of that routine the bot removes | **to be measured** | A/B in the pilot | client + repo evals |

No row is filled with a guess. The two "measures" are the point of the pilot: without them the
business case is a brochure.

## Cost per answer

Base: 0.0306 ₽. Recomputed with the same price list, per tokenizer where it matters:

| Change | ₽/answer | vs base |
|---|---|---|
| Base: 5 chunks, 700-char answer, `bge-reranker-v2-m3` | 0.0306 | — |
| Chunks at p95 size (299 tokens) | 0.0351 | +15% |
| Eight chunks instead of five | 0.0389 | +27% |
| Answer at the 700-token profile ceiling | 0.0370 | +21% |
| Worst case: eight p95 chunks and the ceiling | 0.0524 | +71% |
| Reranker on `Qwen3-Reranker-0.6B` instead | 0.0345 | +13% |
| Chat on `GigaChat 3 Pro` | 0.1936 | ×6.3 |
| Chat on `DeepSeek V4 Flash` | 0.1349 | ×4.4 |

The range 0.031–0.052 ₽ holds under every geometric change. Only the choice of chat model moves the
number materially, and even the most expensive sensible model stays under 0.27 ₽.

## Monthly cost at a given volume

`answers/month × 0.0306 ₽`, plus the fixed platform cost that is **not** in this document (host,
Postgres, backups, monitoring: quotes, see [vendor-comparison](vendor-comparison.md)).

| Answers/month | Variable ₽/month | What that volume looks like |
|---|---|---|
| 2 000 | 61 | a pilot of ~100 newcomers |
| 20 000 | 612 | one plant |
| 100 000 | 3 060 | a company of 5 000 employees at 20 answers each |
| 1 000 000 | 30 600 | above any realistic onboarding load |

The variable line is not the budget. The platform and the people are.

## Self-hosted GPU: what it really costs

Fixed, from VK Cloud (class A, with VAT, 30 days):

| Item | ₽/month | Status |
|---|---|---|
| L4 24 GB | 71 456 | list price |
| L40S 48 GB | 173 479 | list price |
| Model weights | 0 | MIT / Apache-2.0 |
| Corpus reindex | 0 | local |
| Ops owner (0.25–0.5 FTE) | **quote** | not priced here |
| Backup, monitoring, storage, second node for HA | **quote** | not in the price list |
| Throughput on that card | **unmeasured** | needs a load test |

Without the last three lines the GPU looks cheaper than it is. With them, at onboarding volume, it
is not cheaper at all:

```
break-even answers/month = 71 456 ÷ 0.0306 ≈ 2.3 million
```

A company of 5 000 employees at 20 answers each produces 0.1 million per month — 23× below the
break-even. The managed API stays cheaper until roughly 11 000 employees, and even then the GPU
needs an owner who does not exist in the pilot team.

## The comparison that actually decides

| Criterion | Managed RU API | Self-hosted GPU |
|---|---|---|
| Variable cost | 0.031 ₽/answer | unmeasured |
| Fixed cost | ≈ 0 | 71 456 ₽/month |
| Time to first answer | a profile and a key | a week of setup, a load test, an owner |
| Data contour | vendor's Russian region, with an errand of processing | fully inside the operator's contour |
| Vendor failure | escalate to a human, second profile ready | the box is yours to fix |
| Model choice | the vendor's catalogue | anything with a licence |
| Compliance paperwork | errand of processing, attestation of the vendor's segment | the operator's own attestation |

The GPU wins on exactly two rows: the contour and the model choice. If the client needs neither, the
managed API is the answer.

## HR economics: the inputs that matter

The assistant is worth what it frees. That is computed from client data, not from the vendor's price:

```
hours_freed_per_month = newcomers_per_month × minutes_saved_per_newcomer ÷ 60
saving_per_month      = hours_freed_per_month × hourly_HR_cost
payback_months        = setup_cost ÷ (saving_per_month − opex_per_month)
```

What the repo can contribute is one honest anchor: at a loaded HR cost of 90 000 ₽/month (an
illustration, not a client input), one HR minute costs ≈ 8.9 ₽, so **one bot answer at 0.031 ₽ costs
about 0.2 seconds of HR time**. Whatever the pilot measures for `minutes_saved_per_newcomer`, the
model cost will not be the limiting term.

The brief's "up to 70% less routine HR work" is the client's expectation, not our measurement, and
this document does not repeat it as a result.

## Costs the per-answer number hides

| Cost | How to price it | Owner |
|---|---|---|
| App host, Postgres, object storage | invoice from the chosen Russian cloud | DevOps |
| Backups and restore drills | storage + the drill time twice a year | DevOps |
| Monitoring, on-call, incident response | 0.25–0.5 FTE | DevOps |
| 152-ФЗ paperwork | legal hours; errand of processing, DPA review | client DPO |
| Corpus maintenance | HR edits knowledge, reindex is one command | HR + engineer |
| Vendor switch | one day of work + ~4 ₽ of eval tokens | engineer |
| Retention storage | grows with `DATA_RETENTION_DAYS`, unmeasured | client policy |
| Price change | vendor's right; ask for a 90-day lock | procurement |

## Decision triggers

Written down so that the choice is revisited on evidence, not on mood:

| Trigger | Action |
|---|---|
| Measured answers/month > 2 million | re-open the GPU comparison with a real load test |
| A vendor publishes a price validity term and it is ≥ 90 days | prefer that vendor at equal quality |
| `make eval` on a cheaper profile stays green | move down the price list |
| Escalation rate rises above the gate on a cheaper model | move back up; quality is the product |
| The client requires the data to stay in its own contour | GPU or on-prem, cost becomes secondary |
| Errand of processing cannot be signed for the vendor's segment | same as above |
| One vendor outage costs more than the GPU difference | second vendor or GPU, decided by numbers from the pilot |

## Gates before a purchase order

1. `make eval` green on the candidate profile, with a measurement file under `docs/measurements/`.
2. Errand of processing signed; data localised per 152-ФЗ; evidence pack per
   [152fz-checklist.md](../runbooks/152fz-checklist.md).
3. Written offer with currency, VAT, price validity term, volume break, and price-change clause.
4. Written answer on training on our data: off.
5. A named owner for the deployment, with the on-call hours in their plan.
6. Exit plan: who reindexes, how long, what it costs.

## What this document does not claim

- It does not claim savings. Two of the three inputs that produce savings belong to the client.
- It does not price the platform: those are quotes, and a number invented here would be a lie with a
  decimal point.
- It does not compare answer quality across vendors; only [evals](../evals/README.md) do that, per
  profile, with a measurement file.
- It does not treat the break-even as a recommendation. It is a division with a reason attached.
