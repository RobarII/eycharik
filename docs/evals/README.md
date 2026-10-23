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
| `leak_rate` | share of guarded cases where a forbidden document reached the top 5 | = 0.00 |
| `p95_latency_ms` | answer latency on the set, warm cache excluded | ≤ 8000 |
| `cost_per_answer_rub` | provider cost divided by cases | recorded, no gate |

`recall@5` runs without a model. `citation_support` and `escalation_correctness` appear only when
the runner generates answers (`--retrieval-only` skips them). `leak_rate` appears whenever the set
has a guarded case, and it is measured in both modes: a document the viewer may not see is a
confidentiality and validity failure, not a recall gap. `p95_latency_ms` appears only when at
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

- id: salary-bands-blocked
  question: "Покажи вилки окладов по грейдам"
  audience: all
  expect_escalation: true
  expect_reason: no_sources
  expect_absent_docs: [hr/salary-bands]
```

Escalation cases use `expect_escalation: true` and `expect_reason`. `expect_absent_docs` names the
documents that must not appear in the top five: expired editions, `hr_only` and `dept:` material the
viewer does not own, and `draft` documents that are never indexed. A case cannot both expect and
forbid the same document, and `make check` fails when a corpus document has no case at all.

## What the set has to look like

The set is only honest if retrieval has something to fail on:

- every document in `knowledge/` has at least one case, kept by a test;
- same-topic documents compete: two policies with different numbers, an expired edition next to a
  current one, one document in `all` and its neighbour in `hr_only`;
- questions are phrased the way a new hire asks them, not with the words of the document, so a
  lexical match is not a free pass;
- the corpus is written before the questions, and questions are never rewritten after a run to make
  a gate pass.

One caveat travels with every measurement: when the same person writes the corpus and the questions,
recall numbers lean optimistic. Record that in the measurement note instead of claiming the corpus
is neutral.

## Test tiers

Two tiers, and the cheap one is the default:

| Command | What runs | Cost |
|---|---|---|
| `make test` | unit suite, offline; an unmarked test that opens a socket fails | free, ~5 s |
| `make test-live` | `integration` (real Postgres) and `eval` (real providers) | cents, keys required |

`pytest` is configured with `-m 'not integration and not eval'`, so a forgotten marker cannot spend
money on a normal run. `apps/api/tests/conftest.py` blocks the transport and the socket layer; the
guard is itself tested, because "we do not call out" has to be provable. Live model smoke tests are
`apps/api/tests/test_live_providers.py`: one short completion, two sentences, two documents — enough
to prove that the key, the base URL, the extra headers, and the profile agree.

Quality is not in this table on purpose. A smoke test says the wiring works; only `make eval` and
`make eval-retrieval` say whether the answers are good.

## Determinism

A hosted embedding endpoint is not required to be deterministic, and one of them is not: Qwen3
Embedding 8B behind OpenRouter returned cosine 0.997 between two calls with identical input. On the
132-case set that moved `recall@5` between 0.992 and 1.000 across runs and flipped a single case
(`company-products`) between 0.00 and 1.00.

The reranker was stable across three repeats on the same input. The embedder is the noisy leg.

Rules that follow:

- a delta below ~0.02 in `recall@5` on this set is inside provider noise; repeat the run before
  claiming it;
- never compare two embedders using one run each;
- when a case flips between runs, the measurement says so rather than reporting the friendlier run.

## Adding a case

1. Every escalation in production becomes a case.
2. Every wrong answer found by a recruiter becomes a case.
3. A case names documents, not chunks: chunk ids change when chunking changes.
4. The set grows; cases are never deleted to make the gate pass.

## Sentiment set

`docs/evals/sentiment.yaml` is the risk radar's own set: a free-text answer, its tone, the tags a
recruiter would route, and whether a recruiter must be alerted. It answers a different question than
the golden set ("did the model hear the problem?" rather than "did it cite the right document?").
The label rules are in [sentiment-guide.md](sentiment-guide.md); they change before a label does.

```bash
make eval-sentiment                      # the configured prompt classifier
make eval-sentiment PROVIDER=keyword     # deterministic baseline, no key
make eval-sentiment PROVIDER=jev         # TypeSafe Jev, needs JEV_API_KEY
make eval-sentiment SPLIT=test REPEAT=3  # the locked half, three calls per case
```

Every case carries `split: dev | test`. `dev` may be read while editing a prompt; `test` is locked
and every quality claim quotes both numbers, because a gap between them is how overfitting shows
up. The set has two rules: a case is added after a real failure, and no case is deleted to make a
gate pass.

Metrics:

| Metric | Definition |
|---|---|
| `sentiment_accuracy` | share of calls whose tone matches the label, with a Wilson 95% interval |
| `sentiment_macro_f1` | mean F1 over the tones present, so a rare class is not diluted by a common one |
| per-tone recall | one row per tone, plus a confusion matrix; accuracy alone hides a dead class |
| `tag_precision`, `tag_recall`, `tag_f1` | micro over calls and labels, comparable with earlier runs |
| per-tag recall | one row per tag, because a missing `integration` tag is invisible in a micro average |
| `escalation_recall` | share of `expect_escalation` cases where `core/risk.py` returns high + recruiter |
| `false_alarm_rate` | share of calm cases that still escalate |
| `fallback_rate`, `format_error_rate` | how often the classifier degraded to keywords or a broken answer |
| `p50/p95/p99_latency_ms` | per-call latency; p95 alone hides whether the median is already slow |
| `cost_rub_total`, `cost_rub_per_1k_calls` | what the run spent, summed from the classifier's own usage; a price nobody measured is a guess |

`--repeat N` calls the provider N times per case and lists the cases whose verdict changed. A gate
cannot be tighter than that instability.

The Markdown header names what ran: the model, the prompt version, or the rubric selector
(`sentiment-jev@1`). A table without that line is not comparable with anything.

Each run writes two files: the Markdown table and a JSONL artifact with one line per call. The
artifact is what makes a comparison honest:

```bash
python -m onboarding.evals.sentiment --provider prompt --split test \
  --compare docs/measurements/<date>-sentiment-keyword.jsonl
```

`--compare` runs a paired bootstrap over the cases both runs scored and reports the delta with a 95%
interval and `p(delta <= 0)`. Two standalone accuracies are not a comparison; the same cases
resampled together are.

There is no gate yet: a gate needs a stable baseline across models and repetitions. The current
numbers, and the reason Jev has no row, are in
[decisions/0011-jev-sentiment-pilot.md](../decisions/0011-jev-sentiment-pilot.md). A missed crisis
becomes a case here before it becomes a prompt edit.

## OCR set

`docs/evals/ocr.yaml` measures the other half of ingestion: can the pipeline read a page, and does it
refuse a page it cannot read? The cases are rendered from known text with a system font on every run,
so the reference is exact and no binary is committed.

```bash
make eval-ocr                            # doc-scan profile, needs the ocr extra
make eval-ocr ARGS="--write --label v1"  # also write a measurement file
```

Metrics: `character_error_rate` (character edits over reference length, on accepted cases),
`verdict_correctness` (share of cases whose accept/refuse decision and reason match), and
`mean_confidence`. Gates: `character_error_rate ≤ 0.05`, `verdict_correctness = 1.00`.

This is a floor, not a field measurement. A clean render has no perspective, no shadow, no stamp, and
no handwriting: it proves the language route, normalization, and acceptance work, and it will not
notice that the recognizer struggles with a photographed page. The quality gate is not exercised
either — its thresholds ship unset, and turning one on is a measurement of its own. Report a real
accuracy claim only from a set of real scans under `docs/evals/`, with the same command-commit
discipline as the golden set.

## Reporting

A run writes `docs/measurements/<date>-eval-<scope>.md` with the command, the commit, the answer
profile and model, the embedder, and the table of metrics. The profile name is the thing a later
reader can re-run: `LLM_PROFILE=<name> make eval`. Use `--note` for a caveat that must travel with the numbers. A
measurement without a commit is not a measurement.
