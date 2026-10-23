# Eval 2026-10-23 — PASS

- command: `python -m onboarding.evals --write`
- commit: `8ba530d`
- model: `openai/openai/gpt-4.1-mini @ https://openrouter.ai/api/v1`
- environment: `local`
- embed provider: `openai`
- retrieval: `openai/baai/bge-m3 + rerank:cohere/rerank-v3.5`
- cases: 16 (12 general + 4 on the client's own documents: anti-corruption, commercial secret)
- generated answers: True

| metric | value | gate |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.90 |
| `mrr` | 1.000 | >= 0.75 |
| `citation_support` | 1.000 | >= 1.00 |
| `escalation_correctness` | 1.000 | >= 0.90 |
| `answer_contains` | 1.000 | >= 1.00 |
| `p95_latency_ms` | 2237.000 | <= 8000.00 |
| `cost_per_answer_rub` | 0.077 |  |

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
| `gift-limit` | 1.00 | 1.00 | False | answered |
| `report-bribery` | 1.00 | 1.00 | False | answered |
| `commercial-secret-scope` | 1.00 | 1.00 | False | answered |
| `guest-photo-permission` | 1.00 | 1.00 | False | answered |
