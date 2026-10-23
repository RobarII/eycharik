# Observability

What the process exposes, what to alert on, and what it deliberately does not collect.

## What is exposed

`GET /metrics` returns the Prometheus text format. The endpoint is unauthenticated like `/healthz`;
put it behind the ingress allow-list, never on the public internet.

| metric | type | labels | meaning |
|---|---|---|---|
| `onboarding_http_requests_total` | counter | `method`, `route`, `status` | requests by route template; unknown paths collapse to `unmatched` |
| `onboarding_http_request_seconds` | histogram | `method`, `route` | request latency |
| `onboarding_answer_total` | counter | `reason`, `escalated` | answers by grounding verdict |
| `onboarding_answer_stage_seconds` | histogram | `stage` = `retrieval`, `rerank`, `generate` | pipeline latency, the part the webhook cannot see |
| `onboarding_answer_citations` | histogram | — | citations per answer |
| `onboarding_llm_tokens_total` | counter | `direction` = `input`, `output` | provider usage |
| `onboarding_answer_cost_rub_total` | counter | — | answer cost from the provider's token prices |

Every non-health request gets an `X-Request-ID` response header and one JSON log line
`{"event":"http_request",...}`. The webhook work happens asynchronously; correlate it through the
audit log, which stores the same `answer_completed` fields plus the run and employee id.

Metrics are per process. With two API replicas the scraper sums counters; histograms need
`histogram_quantile` per instance first, then a max across instances, or a real metrics backend.

## What to alert on

Thresholds are policy, not measurements. The latency budget is 8000 ms (ADR 0009); the eval p95 is
recorded in `docs/measurements/`.

```promql
# 95% of answer-stage time above 8 s for 10 minutes
histogram_quantile(0.95,
  sum by (le, stage) (rate(onboarding_answer_stage_seconds_bucket[10m]))
) > 8

# the assistant is escalating instead of answering
sum(rate(onboarding_answer_total{escalated="true"}[10m]))
  /
sum(rate(onboarding_answer_total[10m])) > 0.30

# provider calls are failing before an answer exists
rate(onboarding_http_requests_total{status=~"5.."}[5m]) > 0

# spend is running away
increase(onboarding_answer_cost_rub_total[1h]) > 100
```

The first two are the product signals: latency and refusal. A 5xx burst on `/webhook` is a MAX
delivery problem, not an answer problem.

## What is not collected

- No question text, employee id, chat id, or document title in labels. Cardinality and personal
  data both stay out of the metrics endpoint.
- No prompt or completion bodies in logs. The audit log already stores the minimum needed for the
  risk radar, under the retention policy in `docs/product/roles.md`.
- No external tracing yet. A trace needs a collector and a sampling policy; the stage histogram is
  the cheap first step and answers the same latency question.

## Local check

```bash
make run
curl -s localhost:8000/metrics | grep onboarding_answer
```

If the file is empty, no answer has been produced in this process yet. `/metrics` itself and
`/healthz` are not logged to keep the access log readable.
