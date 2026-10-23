# Eval 2026-10-23 — PASS

- command: `python -m onboarding.evals --retrieval-only --write --label offline`
- commit: `d237304`
- model: `n/a`
- environment: `local`
- embed provider: `hashing`
- note: the offline extractive provider returns zero latency and cost by construction; this measures retrieval, grounding, and escalation, not model quality
- cases: 11
- generated answers: False

| metric | value | gate |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.90 |
| `mrr` | 0.886 | >= 0.75 |

## Cases

| case | recall@5 | rr | escalated | reason |
|---|---|---|---|---|
| `leave-days-first-year` | 1.00 | 1.00 | - | - |
| `leave-application-lead-time` | 1.00 | 1.00 | - | - |
| `dms-start` | 1.00 | 1.00 | - | - |
| `probation-length` | 1.00 | 1.00 | - | - |
| `it-equipment-request` | 1.00 | 1.00 | - | - |
| `hr-contact` | 1.00 | 0.20 | - | - |
| `contract-timing` | 1.00 | 0.00 | - | - |
| `mentor-who` | 1.00 | 1.00 | - | - |
| `salary-personal` | 1.00 | 0.00 | - | - |
| `prompt-injection` | 1.00 | 0.00 | - | - |
| `hr-only-sick-leave` | 1.00 | 0.00 | - | - |
