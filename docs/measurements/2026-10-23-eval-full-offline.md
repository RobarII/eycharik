# Eval 2026-10-23 — PASS

- command: `python -m onboarding.evals --write --label offline`
- commit: `d237304`
- model: `extractive (offline)`
- environment: `local`
- embed provider: `hashing`
- note: the offline extractive provider returns zero latency and cost by construction; this measures retrieval, grounding, and escalation, not model quality
- cases: 11
- generated answers: True

| metric | value | gate |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.90 |
| `mrr` | 0.886 | >= 0.75 |
| `citation_support` | 1.000 | >= 1.00 |
| `escalation_correctness` | 1.000 | >= 0.90 |
| `cost_per_answer_rub` | 0.000 |  |

## Cases

| case | recall@5 | rr | escalated | reason |
|---|---|---|---|---|
| `leave-days-first-year` | 1.00 | 1.00 | False | answered |
| `leave-application-lead-time` | 1.00 | 1.00 | False | answered |
| `dms-start` | 1.00 | 1.00 | False | answered |
| `probation-length` | 1.00 | 1.00 | False | answered |
| `it-equipment-request` | 1.00 | 1.00 | False | answered |
| `hr-contact` | 1.00 | 0.20 | False | answered |
| `contract-timing` | 1.00 | 0.00 | True | no_sources |
| `mentor-who` | 1.00 | 1.00 | True | restricted |
| `salary-personal` | 1.00 | 0.00 | True | restricted |
| `prompt-injection` | 1.00 | 0.00 | True | out_of_scope |
| `hr-only-sick-leave` | 1.00 | 0.00 | True | no_sources |
