# Sentiment eval — prompt

- command: `python -m onboarding.evals.sentiment --provider prompt --write --label gpt-4.1-mini`
- commit: `5070a0f`
- environment: `local`
- cases: 16

| metric | value |
|---|---|
| `sentiment_accuracy` | 0.875 |
| `tag_precision` | 0.808 |
| `tag_recall` | 0.913 |
| `fallback_rate` | 0.062 |
| `p95_latency_ms` | 2127.5 |

| case | expected | got | tags |
|---|---|---|---|
| `manager-support` | positive | positive | manager, integration |
| `workload-ok` | neutral | positive | workload, clarity |
| `crisis-quit` | negative | negative | workload |
| `neutral-facts` | neutral | positive | access, other |

