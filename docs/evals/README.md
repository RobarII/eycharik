# Evals

The golden set is the only defence against "it looked good in the demo". It runs on every pull
request that touches retrieval, prompts, or the answer policy.

## Metrics

| Metric | Definition | Gate |
|---|---|---|
| `recall@5` | share of cases whose expected document id is in the top 5 | ≥ 0.90 |
| `mrr` | mean reciprocal rank of the first expected document | ≥ 0.75 |
| `citation_support` | share of answers whose every citation was retrieved for that question | = 1.00 |
| `escalation_correctness` | share of cases whose escalation flag and reason match | ≥ 0.90 |
| `p95_latency_ms` | answer latency on the set, warm cache excluded | ≤ 3000 |
| `cost_per_answer_rub` | provider cost divided by cases | recorded, no gate |

`recall@5` runs without a model. `citation_support` and `escalation_correctness` appear only when
the runner generates answers (`--retrieval-only` skips them). `p95_latency_ms` appears only when at
least one completion reports a non-zero latency, so an offline provider does not score a fake zero.
The offline provider makes generation deterministic too, but it measures the pipeline, not a
model's answer quality.

## Case format

`golden.yaml` → list of cases:

```yaml
- id: leave-28-days
  question: "Сколько дней отпуска в первый год?"
  audience: all
  expect_docs: [hr/leave-policy]
  expect_contains: ["28"]
```

Escalation cases use `expect_escalation: true` and `expect_reason`.

## Adding a case

1. Every escalation in production becomes a case.
2. Every wrong answer found by a recruiter becomes a case.
3. A case names documents, not chunks: chunk ids change when chunking changes.
4. The set grows; cases are never deleted to make the gate pass.

## Reporting

A run writes `docs/measurements/<date>-eval-<scope>.md` with the command, the commit, the model,
and the table of metrics. A measurement without a commit is not a measurement.
