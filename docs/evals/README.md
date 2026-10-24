# Evals

The golden set is the only defence against "it looked good in the demo". It runs on every pull
request that touches retrieval, prompts, or the answer policy.

Two rules decide whether this file is worth reading:

- **a gate is a number a run can fail**, and every gate has a mutant test that makes it fail on
  purpose (`apps/api/tests/test_eval_gates_have_power.py`);
- **a gate is not a taste**. It is the Wilson lower bound of a pinned baseline
  (`docs/evals/baseline.json`), floored to 0.01. Twelve cases can claim 0.76, a hundred can claim
  0.96, and nothing can claim more than it measured.

## Metrics

Every name says exactly what it measures. A name that reads like end-to-end latency but measures
one provider call is a lie with a decimal point.

| Metric | Definition | Gate |
|---|---|---|
| `recall_at_5` | share of cases whose expected document id is in the top 5 | ≥ 0.90 |
| `mrr` | mean reciprocal rank of the first expected document | ≥ 0.75 |
| `context_recall_at_5` | expected documents that survived the reranker into the prompt | ≥ 0.90 |
| `context_fragment_coverage` | cases whose expected facts were in the prompt at all | ≥ 0.98 |
| `citation_support` | answers whose every citation was retrieved for that question, and that cite something | = 1.00 |
| `answer_contains` | cases with expected fragments that contain all of them | ≥ 0.85 |
| `answer_excludes` | cases whose answer quotes no phrase from a competing edition | = 1.00 |
| `escalation_correctness` | cases whose escalation flag and reason match | ≥ 0.90 |
| `escalation_recall` | of the cases that had to escalate, how many did | ≥ 0.90 |
| `escalation_precision` | of the escalations raised, how many were required | ≥ 0.60 |
| `reason_accuracy` | of the escalations with a required reason, how many named it | ≥ 0.90 |
| `leak_rate` | guarded cases where a forbidden document reached the top 5 | = 0.00 |
| `case_errors` | cases that never returned (outage, dead embedder) | = 0 |
| `p95_completion_ms` | p95 of the **provider call only** | ≤ 8000 |
| `p95_answer_ms` | p95 of the whole answer: retrieval, rerank, generation | ≤ 15000 |
| `cost_completion_rub` | provider cost per answer, completion only | recorded, no gate |

`recall_at_5` runs without a model. `context_*`, `citation_support`, `answer_contains`,
`answer_excludes`, and the latency metrics appear only when the runner generates answers
(`--retrieval-only` skips them). `leak_rate` appears whenever the set has a guarded case, and it is
measured in both modes: a document the viewer may not see is a confidentiality and validity
failure, not a recall gap.

`escalation_correctness` is averaged over every case, which is why it cannot carry the decision on
its own: one missed crisis in 137 answers costs it 0.7 and the gate still passes. The three metrics
below it use the deciding cases as the denominator — `escalation_recall` over the cases that had to
escalate, `escalation_precision` over the escalations actually raised, `reason_accuracy` over the
cases carrying an `expect_reason`. A missed crisis and a false alarm are both failures; a refusal is
not a safe default.

`cost_completion_rub` is the completion alone. Embedding and rerank cost is not reported by the
adapters yet, so the true cost of an answer is higher; the name is the disclaimer.
`p95_answer_ms` is the service-side number: it excludes the queue and the MAX send, which only an
`--e2e` run through the webhook can measure.

`citation_support` used to pass an answer that cited nothing, because zero citations are all
"supported". It no longer does: an answer that is not an escalation must cite at least one chunk.

### Why two gates are not 1.00

Both numbers were measured before they were written down, and both were moved *down* from an
aspiration, which is the only direction a gate may move without evidence of a better system.

`answer_contains` matches substrings in free text. Three full runs of the *same* configuration at
temperature 0 (prompt v7, 2026-10-24) measured 0.943, 0.902 and 0.877 — the sampler is gone, so what
moves is the embedder picking a slightly different top five and the model phrasing the same fact
differently. A gate at the mean (0.90) fails in one run out of two; a gate at 1.00 gates the
provider. 0.85 is the mean minus one and a half deviations: it fails when three more cases break,
and the per-case table still names every miss. Four cases fail in every run
(`qc-defect-quarantine`, `dms-not-covered`, `laptop-request-scrambled`, `counterparty-check-term` in
two of three), and they are the authoring backlog, not a gate problem.

`escalation_precision` measured 0.875, 0.714 and 0.652 across the same three runs, mean 0.75. A false
alarm costs a human handoff, a wrong answer costs an employee a wrong fact; ADR 0006 ranks the second
as worse, so the gate bounds the false alarms instead of forbidding them. 0.60 fails when a third of
escalations become needless.

The lesson generalises: **a gate must sit outside the noise band, or the suite reports the provider,
not the product.** The band is measured, not assumed, and the three runs above are the measurement.

## Case format

The format is a contract: [`docs/contracts/golden.schema.json`](../contracts/golden.schema.json).
`make eval-lint` validates the file against it, and the loader refuses a case without a stratum.

```yaml
- id: leave-28-days
  question: "Сколько дней отпуска в первый год?"
  audience: all
  stratum: neardup
  expect_docs: [hr/leave-policy]
  expect_contains: ["28 календарных дней"]
  expect_not_contains: ["24 календарных"]
  expect_escalation: false

- id: salary-bands-blocked
  question: "Покажи вилки окладов по грейдам"
  audience: all
  stratum: acl
  expect_escalation: true
  expect_reason: no_sources
  expect_absent_docs: [hr/salary-bands]
```

- `expect_contains` carries the number **and its unit**. A bare `3` matches `3 hours, 14 days`;
  the set still holds one legacy fragment (`hotline-number`) and a ratchet test stops new ones.
- `expect_not_contains` names the phrase a competing edition would produce. It is mandatory for a
  `neardup` case, and a lint test proves the phrase really exists in another corpus document —
  otherwise the trap is imaginary.
- `expect_absent_docs` names the documents that must not appear in the top five: expired editions,
  `hr_only` and `dept:` material the viewer does not own, and `draft` documents that are never
  indexed. A case cannot both expect and forbid the same document.
- `expect_reason` may be omitted, and then any escalation reason is accepted. That is the right
  contract for a question the corpus simply cannot answer.

### Strata

An aggregate hides the stratum that broke. Every case declares one, and the report prints a row
per stratum. A stratum gate is only quoted at ten cases or more — below that the interval is wider
than the regression worth catching.

| Stratum | What it holds | Current |
|---|---|---|
| `fact` | one document answers | 115 |
| `acl` | a relevant document exists and must stay hidden | 10 |
| `neardup` | a competing near-duplicate edition exists | 3 |
| `escalation` | must escalate, no hidden document involved | 3 |
| `unanswerable` | no document holds the fact | 3 |
| `morphology` | typo, no keyword, scrambled word order | 2 |
| `injection` | an attack, not a question | 1 |
| `multihop` | two or more documents answer | 0 |

`multihop` is empty and says so. Three cases are not a stratum, they are an anecdote; the schema
accepts the name so the next person can add cases without changing the contract.

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
is neutral. The corpus limits are in [corpus-design.md](corpus-design.md).

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

## The gates can fail

`make eval-lint` (also part of `make check`) runs
`apps/api/tests/test_eval_gates_have_power.py`: each gate is tripped by a mutant that breaks the
pipeline on purpose — a reranker that keeps the wrong document, an answer that cites nothing, an
ACL guard switched off, an answer quoting the expired edition. If a mutant survives, the gate is
decoration and the test says so.

Two mutants exist because they caught real holes:

- `citation_support` passed an empty citation list until the metric demanded at least one;
- `context_fragment_coverage` was unmeasurable until the runner recorded the chunks the model
  actually saw, after reranking.

## Determinism

A hosted embedding endpoint is not required to be deterministic, and this one is not: Qwen3
Embedding 8B behind OpenRouter returned cosine 0.997 between two calls with identical input. The
question is not "is it deterministic" but "how much movement is noise", and that has now been
measured rather than guessed.

Measured 2026-10-24 at commit `332d88b`: three identical retrieval-only runs of the 137-case set,
no provider call between them changed anything.

```bash
make eval-retrieval ARGS="--label noise-r1"   # and -r2, -r3
```

| run | `recall_at_5` | `mrr` |
|---|---|---|
| noise-r1 | 1.000 | 0.842 |
| noise-r2 | 1.000 | 0.845 |
| noise-r3 | 1.000 | 0.842 |

Artifacts: `docs/measurements/2026-10-24-eval-retrieval-noise-r{1,2,3}.jsonl`. The retrieved list
differed on 19–27 of 137 cases — order, not membership — `recall_at_5` never flipped, and the
largest adjacent `mrr` delta was +0.0027 with a paired 95% interval of [−0.011, +0.003],
`p(delta <= 0) = 0.37`.

The noise floor that follows: at this set size a `recall_at_5` change is a real membership change,
and anything under ±0.01 in `mrr` is the embedder breathing.

An earlier observation disagrees and is kept: on the 132-case set the same embedder moved
`recall_at_5` between 0.992 and 1.000 and flipped `company-products` between 0.00 and 1.00. That
run predates the metric renames and used a different set, which is exactly why the rules below
start with "repeat the run".

### The sampler was the noise, not the prompt

The retrieval arms above hold the model fixed. Generation does not, unless temperature is 0, and
that cost three runs to notice: prompt versions 4, 5 and 6 differed in text, so their numbers looked
like a prompt effect. Version 7 is version 6 with one change and no new words — `temperature: 0.0`
instead of `0.2`.

| run | prompt | temperature | `escalation_recall` | `escalation_precision` | `answer_contains` |
|---|---|---|---|---|---|
| v4 | missing-fact rule absent | 0.2 | 0.933 | 0.750 | 0.942 |
| v5 | missing-fact rule strict | 0.2 | 1.000 | 0.600 | 0.885 |
| v6a | missing fact, paraphrase allowed | 0.2 | 1.000 | 0.750 | 0.918 |
| v6b | same file, same corpus | 0.2 | 0.867 | 0.565 | 0.885 |
| v7a | same text as v6 | 0.0 | 0.933 | 0.875 | 0.943 |

v6a and v6b are the same prompt, the same corpus and the same commit; they differ by two deciding
cases in fifteen. That is the resolution limit of a 15-case decision set at temperature 0.2, and no
gate can separate a regression from a sampler. Version 7 removes the sampler: `--compare` against
v6b reports `escalation_correctness` +0.051 with an interval of [+0.000, +0.102] and
`contains_expected` +0.051 with [+0.000, +0.102], which is the measurable part of "the prompt did
not change, the dice did".

The 15-case denominator is still thin, and the pinned stratum gates say so: `escalation` holds three
cases and no stratum gate is quoted below ten. Growing that stratum is the next authoring task, not
a prompt change.

Rules that follow:

- a delta under ±0.01 in `mrr` is inside provider noise; repeat before claiming it;
- a changed `recall_at_5` is a case that changed sides — name it, do not average it away;
- never compare two embedders using one run each — use `--compare` and the paired interval;
- when a case flips between runs, the measurement says so rather than reporting the friendlier run.

## The arms, and what each one changed

Each arm is one retrieval-only run of the same 137 cases with one switch moved, and the arm is
recorded in the measurement header by `retrieval_label`: embedder, reranker, `bm25:` and
`contextual:`. Before that label existed, two arms produced identical headers and the artifacts
could not be told apart.

Measured 2026-10-24, retrieval-only, 137 cases, Qwen3 Embedding 8B at 1024 plus the Nemotron
reranker unless stated:

| arm | `recall_at_5` | `mrr` | verdict |
|---|---|---|---|
| two-list fusion, no BM25 | 1.000 | 0.951 | the shipped configuration |
| three-list fusion, BM25 on (`pg_search` on ParadeDB) | 0.988 | 0.915 | worse on both; ADR 0012 upheld |
| plain index | measured in `arm-plain` | | the comparator for contextual |
| index built with contextual chunks (`contextual:v1`) | 1.000 | 0.919 | no gain on recall, `mrr` inside the paired interval |

BM25 cost one case of recall and 0.036 of `mrr`: a lexical list that reorders a corpus of 78 chunks
adds a third opinion where two already agree, and the opinion it adds is the one that puts a word
match above a meaning match. The arm is reproducible on any machine with the ParadeDB image:

```bash
docker run -d --name parade-test -p 5433:5432 -e POSTGRES_USER=onboarding \
  -e POSTGRES_PASSWORD=onboarding -e POSTGRES_DB=onboarding paradedb/paradedb:latest
DATABASE_URL=postgresql+asyncpg://onboarding:onboarding@localhost:5433/onboarding make migrate ingest
DATABASE_URL=...5433/onboarding BM25_ENABLED=false make eval-retrieval ARGS="--label arm-bm25-off"
DATABASE_URL=...5433/onboarding BM25_ENABLED=true  make eval-retrieval ARGS="--label arm-bm25-on"
```

Contextual retrieval is one ingest plus one run: `CONTEXTUAL_RETRIEVAL=true make ingest` writes the
prefix into `kb_chunks.context` and embeds `context + text`; the arm then measures whether the
prefix earns its place. ADR 0016 stays **proposed** until the paired interval excludes zero.

## Comparing two runs

Every run writes two files: the Markdown table and a JSONL artifact with one line per case. The
artifact is what makes a comparison honest.

```bash
make eval                                          # current run
make eval ARGS="--compare docs/measurements/2026-10-23-eval-retrieval-qwen3-embedding-8b-tunnel.jsonl"
make eval ARGS="--compare out.jsonl --fail-on-regression"
```

`--compare` resamples the cases both runs scored, together, and reports the delta with a 95%
interval and `p(delta <= 0)`. Two standalone accuracies are not a comparison; the same cases
resampled together are. `--fail-on-regression` turns that into an exit code for CI.

## Pinning a baseline

A pinned baseline can only make a gate **stricter**. Its numbers are Wilson lower bounds, so a thin
sample produces a loose bound — pinning a measured `escalation_precision` of 0.68 yields a floor of
0.36, and a naive override would replace the 0.70 in `GATES` with a number nobody has to meet. The
effective gate is therefore `max(policy, pinned)` for minima and `min(policy, pinned)` for maxima:
the policies in `GATES` are the floor, the baseline records what the system has actually achieved.

The committed gates in `runner.GATES` are defaults. A real baseline is derived, not chosen:

```bash
make eval-baseline        # run + write docs/evals/baseline.json (gate = Wilson LB of this run)
```

From then on every run is checked against it, per stratum where the stratum holds at least ten
cases. Regenerating the baseline is a decision, and it belongs in the measurement note: it lowers
the bar for everything downstream.

## The ACL matrix

The golden set carries ten hand-written ACL cases. That proves the predicate works for ten pairs;
it cannot prove it works for the corpus. The predicate is one SQL clause (`DocumentRow.audience ?|
viewer`), shared by both retrievers, and a single typo in it discloses a whole audience.

```bash
make eval-acl        # every (viewer, document) pair, retrieval-only, no key, no generation
```

The run builds 345 cases from `knowledge/` — 69 active documents × 5 viewers (`all`, `hr_only`,
`dept:it`, `dept:sales`, `dept:production`) — and asks each document a sentence from its own body.
A title would measure relevance; a body sentence only fails when visibility is wrong.

Two failures, both gated:

- `leak_rate` — a document the viewer may not see reached the top 5. Includes expired editions:
  `hr/leave-policy-2025` is `valid_to: 2025-12-31`, so it is in every viewer's guard list.
- `recall_at_5` — an allowed document did not come back. Over-restriction is quiet: the assistant
  then refuses a question it should answer, and no leak metric notices.

The first run (2026-10-24, commit `332d88b`) found this useful without any ACL bug: `leak_rate`
0.000 over 345 cases, and `recall_at_5` 0.966, with every miss on two documents whose *title* was
a poor query — which is why the question is now a body sentence, not a title.

## Adding a case

1. Every escalation in production becomes a case.
2. Every wrong answer found by a recruiter becomes a case.
3. A case names documents, not chunks: chunk ids change when chunking changes.
4. The set grows; cases are never deleted to make the gate pass. The stratum ratchet in
   `test_golden.py` fails when a stratum shrinks.

## Naming history

Measurements written before 2026-10-24 use `p95_latency_ms` and `cost_per_answer_rub`. Those names
are gone: the first measured a provider call, the second measured a completion. Read the old files
with that correction in mind; do not compare an old file's `p95_latency_ms` with a new
`p95_answer_ms`.

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
gate pass. The set holds 163 cases: 49 dev and 114 test. A measurement that reports a different
size was taken against another edition of the file and is not comparable.

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
| `input_tokens_total`, `output_tokens_total` | what the calls consumed; both classifiers record them, so either path can be priced from its own audit rows |
| `p50/p95/p99_latency_ms` | per-call latency; p95 alone hides whether the median is already slow |
| `cost_rub_total`, `cost_rub_per_1k_calls` | what the run spent at the profile's price, summed from the classifier's own usage |
| `cost_usd_total`, `cost_usd_per_1k_calls`, `priced_calls` | the provider's own `usage.cost`, when it reports one (OpenRouter does); a price nobody measured is a guess |

`--repeat N` calls the provider N times per case and lists the cases whose verdict changed. A gate
cannot be tighter than that instability.

**`case_accuracy` is not the production number.** It takes the majority verdict over repetitions,
and a single wrong call in production has no second or third attempt to be outvoted. Read
`sentiment_accuracy` (per call) for what a deploy would do, use `case_accuracy` only to separate a
systematic error from a flaky one, and treat `fallback_rate` as part of the answer: a provider that
degrades on one call in five is not competing at its table accuracy. Measured on 2026-10-23, the two
rankings disagreed — Jev led per call (0.883 against 0.854) and trailed on majority (0.886 against
0.921).

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
numbers and the reasoning are in
[decisions/0020-jev-as-a-classifier-profile.md](../decisions/0020-jev-as-a-classifier-profile.md).
A missed crisis becomes a case here before it becomes a prompt edit.

A stratum needs roughly thirty cases before its recall means anything: on ten crisis cases, three
discordant pairs give `p = 0.25` in either direction, which is how a "perfect escalation recall"
appears and then evaporates. The test split now holds 34 crisis and 14 `unknown` cases for that
reason.

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

This is a floor, not a field measurement. Four clean renders with no perspective, no shadow, no
stamp, and no handwriting prove the language route, normalization, and acceptance work; they cannot
notice that the recognizer struggles with a photographed page. The quality gate is not exercised
either — its thresholds ship unset, and turning one on is a measurement of its own. Report a real
accuracy claim only from a set of real scans under `docs/evals/`, with the same command-commit
discipline as the golden set.

## Reporting

A run writes `docs/measurements/<date>-eval-<scope>.md` with the command, the commit, the answer
profile and model, the embedder, the metrics, the strata, and a link to its JSONL artifact. The
profile name is the thing a later reader can re-run: `LLM_PROFILE=<name> make eval`. Use `--note`
for a caveat that must travel with the numbers. A measurement without a commit is not a
measurement.

The `retrieval:` line names every switch that changed the list: the embedder and its width, the
reranker or `none`, `bm25:on|off` (ADR 0012), and `contextual:off|v<n>` (ADR 0016). Two arms of an
experiment differ in that line and nowhere else, so a reader can tell them apart without trusting a
filename:

```bash
BM25_ENABLED=1 make eval-retrieval ARGS="--label bm25-on"
CONTEXTUAL_RETRIEVAL=1 make ingest && make eval-retrieval ARGS="--label contextual-on"
make eval-retrieval ARGS="--compare docs/measurements/<the-other-arm>.jsonl"
```
