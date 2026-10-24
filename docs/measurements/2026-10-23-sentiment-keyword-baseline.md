---
title: "Оценка 2026-10-23: baseline"
summary: "16 кейсов, гейты пройдены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-23 — пройдена

- команда: `python -m onboarding.evals.sentiment --provider keyword --write --label baseline`
- коммит: `5070a0f`
- окружение: `local`
- кейсов: 16

| метрика | значение |
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


Кейсы по одному — в артефакте `2026-10-23-sentiment-keyword-baseline.jsonl` рядом с этим файлом.
