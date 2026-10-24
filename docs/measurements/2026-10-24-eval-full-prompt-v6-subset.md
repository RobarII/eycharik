# Eval 2026-10-24 — FAIL

- command: `python -m onboarding.evals --write --only it-equipment-request,commercial-secret-scope,unpaid-leave-days,maternity-days,guest-wifi,personal-data-third-parties,qc-stages,counterparty-check-term,repair-loaner,training-budget-size,probation-extension-length,sales-contract-blocked,overtime-pay,quality-deviation,dms-family,phishing-drill,ecology-polymer-waste,it-runbook-blocked,hr-only-sick-leave,salary-bands-blocked --label prompt-v6-subset --compare docs/measurements/2026-10-24-eval-full-baseline-v1.jsonl`
- commit: `2fa84b7`
- model: `openai/opencode-deepseek-v4.1-flash (deepseek-v4.1-flash) @ https://opencode.ai/inference/go/v1`
- environment: `local`
- embed provider: `openai`
- retrieval: `openrouter-qwen3-embedding-8b (qwen/qwen3-embedding-8b, dim 1024) + rerank:openrouter-nemotron-rerank-8b (nvidia/nemotron-3.5-rerank-8b:free) + bm25:off + contextual:off`
- artifact: `2026-10-24-eval-full-prompt-v6-subset.jsonl`
- cases: 20
- generated answers: True

| metric | value | gate |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.90 |
| `mrr` | 0.896 | >= 0.75 |
| `leak_rate` | 0.000 | <= 0.00 |
| `context_recall_at_5` | 1.000 | >= 0.90 |
| `context_fragment_coverage` | 0.938 | >= 0.98 |
| `p95_completion_ms` | 10388.000 | <= 8000.00 |
| `p95_answer_ms` | 12970.000 | <= 15000.00 |
| `citation_support` | 1.000 | >= 1.00 |
| `escalation_correctness` | 1.000 | >= 0.90 |
| `escalation_recall` | 1.000 | >= 0.90 |
| `escalation_precision` | 1.000 | >= 0.90 |
| `reason_accuracy` | 1.000 | >= 0.90 |
| `answer_contains` | 0.938 | >= 1.00 |
| `cost_completion_rub` | 0.086 |  |

Failed gates: context_fragment_coverage, answer_contains, p95_completion_ms

## Strata

One aggregate hides the stratum that broke. A gate is quoted per stratum only
when the stratum holds at least 10 cases.

| stratum | cases | recall@5 | context@5 | mrr | escalation | contains |
|---|---|---|---|---|---|---|
| `fact` | 16 | 1.00 | 1.00 | 0.90 | 1.00 | 0.94 |
| `acl` | 4 | 0.00 | - | 0.00 | 1.00 | - |

## Comparison against baseline

Paired bootstrap over the cases both runs scored: two standalone numbers are not a
comparison, the same cases resampled together are.

| metric | current | baseline | delta | 95% CI | p(delta <= 0) | n |
|---|---|---|---|---|---|---|
| `recall` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 20 (-) |
| `context_recall` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 20 (-) |
| `rr` | 0.717 | 0.717 | +0.000 | [+0.000, +0.000] | 1.000 | 20 (-) |
| `citation_supported` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 20 (-) |
| `escalation_correct` | 1.000 | 0.600 | +0.400 | [+0.200, +0.600] | 0.000 | 20 (-) |
| `escalation_matched` | 1.000 | 0.700 | +0.300 | [+0.100, +0.500] | 0.001 | 20 (-) |
| `contains_expected` | 0.950 | 0.750 | +0.200 | [+0.050, +0.400] | 0.013 | 20 (-) |
| `forbidden_clean` | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | 1.000 | 20 (-) |

## Cases

| case | stratum | recall@5 | ctx@5 | rr | leaked | escalated | reason | missing | forbidden |
|---|---|---|---|---|---|---|---|---|---|
| `it-equipment-request` | `fact` | 1.00 | 1.0 | 0.50 | - | False | answered | - | - |
| `hr-only-sick-leave` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `commercial-secret-scope` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `unpaid-leave-days` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `overtime-pay` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `maternity-days` | `fact` | 1.00 | 1.0 | 0.50 | - | False | answered | - | - |
| `guest-wifi` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `personal-data-third-parties` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `salary-bands-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `it-runbook-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `quality-deviation` | `fact` | 1.00 | 1.0 | 0.33 | - | False | answered | - | - |
| `qc-stages` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `counterparty-check-term` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `repair-loaner` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `training-budget-size` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `sales-contract-blocked` | `acl` | 1.00 | 1.0 | 0.00 | - | True | no_sources | - | - |
| `dms-family` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | оплатой 50% | - |
| `phishing-drill` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `probation-extension-length` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |
| `ecology-polymer-waste` | `fact` | 1.00 | 1.0 | 1.00 | - | False | answered | - | - |

## Failures in detail

A failing gate needs the answer that failed it, not just the count: the same number
can mean a wrong fact, a wrong format, or a confidently answered question that should
have escalated.

### `dms-family` — Можно ли застраховать супруга по ДМС?

- stratum: `fact`
- audience: `all`
- escalated: False (expected False)
- escalation reason: answered (expected -)
- missing fragments: оплатой 50%
- forbidden fragments: -
- retrieved: hr/benefits-dms, company/org-structure, hr/expenses, hr/sick-leave-notification
- context: hr/benefits-dms, hr/sick-leave-notification, hr/expenses, hr/sick-leave-pay

```
ДМС распространяется только на самого сотрудника, однако членов семьи можно подключить к программе на условиях страховой: оплата составит 50% из личных средств. За подробностями обратитесь в HR.
```

