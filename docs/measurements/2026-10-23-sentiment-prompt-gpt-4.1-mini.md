---
title: "Оценка 2026-10-23: gpt-4.1-mini"
summary: "16 кейсов, гейты пройдены; команда и коммит в шапке."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-23 — пройдена

- команда: `python -m onboarding.evals.sentiment --provider prompt --write --label gpt-4.1-mini`
- коммит: `5070a0f`
- окружение: `local`
- кейсов: 16

| метрика | значение |
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


Кейсы по одному — в артефакте `2026-10-23-sentiment-prompt-gpt-4.1-mini.jsonl` рядом с этим файлом.
