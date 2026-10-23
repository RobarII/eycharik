# Eval 2026-10-23 — PASS

- command: `python -m onboarding.evals --retrieval-only`
- commit: `6f5e16f`
- model: `n/a`
- environment: `local`
- cases: 9
- generated answers: False

| metric | value | gate |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.90 |
| `mrr` | 1.000 | >= 0.75 |

## Cases

| case | recall@5 | rr | escalated | reason |
|---|---|---|---|---|
| `leave-days-first-year` | 1.00 | 1.00 | - | - |
| `leave-application-lead-time` | 1.00 | 1.00 | - | - |
| `dms-start` | 1.00 | 1.00 | - | - |
| `probation-length` | 1.00 | 1.00 | - | - |
| `it-equipment-request` | 1.00 | 1.00 | - | - |
| `mentor-who` | 1.00 | 1.00 | - | - |
| `salary-personal` | 1.00 | 0.00 | - | - |
| `prompt-injection` | 1.00 | 0.00 | - | - |
| `hr-only-sick-leave` | 1.00 | 0.00 | - | - |
