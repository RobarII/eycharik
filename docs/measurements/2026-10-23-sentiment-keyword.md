# Sentiment eval — keyword

- command: `python -m onboarding.evals.sentiment --provider keyword --write`
- commit: `5070a0f`
- environment: `local`
- cases: 16

| metric | value |
|---|---|
| `sentiment_accuracy` | 0.375 |
| `tag_precision` | 0.850 |
| `tag_recall` | 0.739 |
| `fallback_rate` | 0.000 |
| `p95_latency_ms` | 0.0 |

| case | expected | got | tags |
|---|---|---|---|
| `access-missing` | negative | neutral | access, it |
| `access-fixed` | positive | neutral | access, it |
| `manager-no-feedback` | negative | neutral | manager, clarity |
| `manager-support` | positive | neutral | manager |
| `workload-ok` | neutral | positive | clarity |
| `colleagues-cold` | negative | neutral | it, colleagues |
| `colleagues-warm` | positive | positive | colleagues |
| `clarity-good` | positive | neutral | clarity |
| `hr-documents` | positive | neutral | hr |
| `hr-delay` | negative | neutral | hr |
| `crisis-quit` | negative | unknown |  |

