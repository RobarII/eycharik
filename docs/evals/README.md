# Evals

The golden set is the only defence against "it looked good in the demo". It runs on every pull
request that touches retrieval, prompts, or the answer policy.

## Metrics

| Metric | Definition | Gate |
|---|---|---|
| `recall@5` | share of cases whose expected document id is in the top 5 | ≥ 0.90 |
| `mrr` | mean reciprocal rank of the first expected document | ≥ 0.75 |
| `citation_support` | share of answers whose every citation was retrieved for that question | = 1.00 |
| `answer_contains` | share of cases with expected fragments that contain all of them | = 1.00 |
| `escalation_correctness` | share of cases whose escalation flag and reason match | ≥ 0.90 |
| `p95_latency_ms` | answer latency on the set, warm cache excluded | ≤ 8000 |
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

## Sentiment set

`docs/evals/sentiment.yaml` is the risk radar's own set: a free-text answer, its tone, and the tags
a recruiter would route. It answers a different question than the golden set ("did the model hear
the problem?" rather than "did it cite the right document?").

```bash
make eval-sentiment                      # the configured prompt classifier
make eval-sentiment PROVIDER=keyword     # deterministic baseline, no key
make eval-sentiment PROVIDER=jev         # TypeSafe Jev, needs JEV_API_KEY
```

Metrics: `sentiment_accuracy`, `tag_precision`, `tag_recall`, `fallback_rate`, `p95_latency_ms`.
There is no gate yet: the set is the pilot's yardstick, and a gate needs a stable baseline across
models. A missed crisis becomes a case here before it becomes a prompt edit.

## Reporting

A run writes `docs/measurements/<date>-eval-<scope>.md` with the command, the commit, the model,
and the table of metrics. Use `--note` for a caveat that must travel with the numbers. A
measurement without a commit is not a measurement.
