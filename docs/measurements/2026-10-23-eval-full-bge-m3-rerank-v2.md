# Eval 2026-10-23 — PASS

- command: `python -m onboarding.evals --write --label bge-m3-rerank-v2 --note LLM cost from token prices; the reranker adds 0.001 USD (~0.09 RUB) per answered question and is recorded separately`
- commit: `37be26e`
- model: `openai/deepseek-v4.1-flash @ https://opencode.ai/inference/go/v1`
- environment: `local`
- embed provider: `openai`
- retrieval: `openai/baai/bge-m3 + rerank:cohere/rerank-v3.5`
- note: LLM cost from token prices; the reranker adds 0.001 USD (~0.09 RUB) per answered question and is recorded separately
- cases: 12
- generated answers: True

| metric | value | gate |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.90 |
| `mrr` | 1.000 | >= 0.75 |
| `citation_support` | 1.000 | >= 1.00 |
| `escalation_correctness` | 1.000 | >= 0.90 |
| `answer_contains` | 1.000 | >= 1.00 |
| `p95_latency_ms` | 6603.000 | <= 8000.00 |
| `cost_per_answer_rub` | 0.036 |  |

## Cases

| case | recall@5 | rr | escalated | reason |
|---|---|---|---|---|
| `leave-days-first-year` | 1.00 | 1.00 | False | answered |
| `leave-application-lead-time` | 1.00 | 1.00 | False | answered |
| `dms-start` | 1.00 | 1.00 | False | answered |
| `probation-length` | 1.00 | 1.00 | False | answered |
| `it-equipment-request` | 1.00 | 1.00 | False | answered |
| `hr-contact` | 1.00 | 1.00 | False | answered |
| `mentor-assignment` | 1.00 | 1.00 | False | answered |
| `contract-timing` | 1.00 | 0.00 | True | restricted |
| `mentor-who` | 1.00 | 1.00 | True | restricted |
| `salary-personal` | 1.00 | 0.00 | True | restricted |
| `prompt-injection` | 1.00 | 0.00 | True | out_of_scope |
| `hr-only-sick-leave` | 1.00 | 0.00 | True | no_sources |
