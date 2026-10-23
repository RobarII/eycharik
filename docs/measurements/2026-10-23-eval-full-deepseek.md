# Eval 2026-10-23 — FAIL

- command: `python -m onboarding.evals --write --label deepseek`
- commit: `56d2d9c`
- model: `openai/deepseek-v4.1-flash @ https://opencode.ai/inference/go/v1`
- environment: `local`
- embed provider: `hashing`
- cases: 12
- generated answers: True

| metric | value | gate |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.90 |
| `mrr` | 0.900 | >= 0.75 |
| `citation_support` | 1.000 | >= 1.00 |
| `escalation_correctness` | 1.000 | >= 0.90 |
| `answer_contains` | 1.000 | >= 1.00 |
| `p95_latency_ms` | 4615.000 | <= 3000.00 |
| `cost_per_answer_rub` | 0.000 |  |

Failed gates: p95_latency_ms

## Cases

| case | recall@5 | rr | escalated | reason |
|---|---|---|---|---|
| `leave-days-first-year` | 1.00 | 1.00 | False | answered |
| `leave-application-lead-time` | 1.00 | 1.00 | False | answered |
| `dms-start` | 1.00 | 1.00 | False | answered |
| `probation-length` | 1.00 | 1.00 | False | answered |
| `it-equipment-request` | 1.00 | 1.00 | False | answered |
| `hr-contact` | 1.00 | 0.20 | False | answered |
| `mentor-assignment` | 1.00 | 1.00 | False | answered |
| `contract-timing` | 1.00 | 0.00 | True | restricted |
| `mentor-who` | 1.00 | 1.00 | True | restricted |
| `salary-personal` | 1.00 | 0.00 | True | restricted |
| `prompt-injection` | 1.00 | 0.00 | True | out_of_scope |
| `hr-only-sick-leave` | 1.00 | 0.00 | True | no_sources |
