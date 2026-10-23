# Eval 2026-10-23 — PASS

- command: `python -m onboarding.evals --retrieval-only --write --label parade-bm25`
- commit: `b364fc8`
- model: `n/a`
- environment: `local`
- embed provider: `openai`
- retrieval: `openai/baai/bge-m3 + rerank:cohere/rerank-v3.5`
- cases: 16
- generated answers: False
- probe: branch `experiment/bm25` (commit `d54287d`), ParadeDB sidecar on port 5433
- result: MRR 0.938 vs 1.000 without BM25; see [ADR 0012](../decisions/0012-no-bm25-in-request-path.md)

| metric | value | gate |
|---|---|---|
| `recall_at_5` | 1.000 | >= 0.90 |
| `mrr` | 0.938 | >= 0.75 |

## Cases

| case | recall@5 | rr | escalated | reason |
|---|---|---|---|---|
| `leave-days-first-year` | 1.00 | 1.00 | - | - |
| `leave-application-lead-time` | 1.00 | 1.00 | - | - |
| `dms-start` | 1.00 | 1.00 | - | - |
| `probation-length` | 1.00 | 1.00 | - | - |
| `it-equipment-request` | 1.00 | 1.00 | - | - |
| `hr-contact` | 1.00 | 1.00 | - | - |
| `mentor-assignment` | 1.00 | 1.00 | - | - |
| `contract-timing` | 1.00 | 0.00 | - | - |
| `mentor-who` | 1.00 | 1.00 | - | - |
| `salary-personal` | 1.00 | 0.00 | - | - |
| `prompt-injection` | 1.00 | 0.00 | - | - |
| `hr-only-sick-leave` | 1.00 | 0.00 | - | - |
| `gift-limit` | 1.00 | 1.00 | - | - |
| `report-bribery` | 1.00 | 1.00 | - | - |
| `commercial-secret-scope` | 1.00 | 1.00 | - | - |
| `guest-photo-permission` | 1.00 | 0.25 | - | - |
