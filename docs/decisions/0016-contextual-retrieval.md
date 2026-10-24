# 0016 — Contextual retrieval at ingest, proposed

Status: **proposed**. Nothing in a deployed configuration turns it on.

## The problem it is meant to solve

A chunk is a document with its edges cut off. `hr/unpaid-leave` splits into a second chunk that
opens with «Заявление подаётся не позднее чем за три рабочих дня» — a sentence that is true, useful,
and unreachable, because it names neither the leave type nor the document. An embedding of that
sentence is close to every other deadline in the corpus.

The document title is not lost — it is a column on the parent row — but the embedder never sees it,
and neither does `ts_rank_cd`.

## What the recipe does

Anthropic's contextual retrieval prepends a short, model-written sentence to each chunk before it is
embedded: which document this is, which section, what conditions apply. The chunk then competes with
the sections that did name the topic.

Three details matter more than the recipe itself:

1. **The context is generated once, at ingest.** It is a corpus property, not a request property.
   The request path gains no latency and no failure mode.
2. **The context is prepended for indexing only.** `kb_chunks.text` keeps the quotable source;
   `kb_chunks.context` holds the generated prefix, and `Chunk.embedding_text` joins them. A citation
   must never quote a model, so the two stay in separate columns and the prompt layer reads `text`.
3. **A failure aborts the batch.** A corpus half indexed with context and half without is worse
   than one indexed without: relevance becomes silently document-dependent, and no eval can tell
   which half it measured.

## Why it is not accepted yet

The same reason as [0012](0012-no-bm25-in-request-path.md): no measured failure to fix. On the
132-case golden set the current hybrid retrieval reaches `recall@5 = 0.985` and `mrr = 0.913`, and the
corpus is 78 chunks. At that size a chunk rarely loses its document, because almost every document
is one chunk.

The cost side is real: one completion per chunk at ingest, a new prompt version and its eval, a
column, and a reindex. The benefit side is currently zero measured.

## What would make it accepted

- a corpus where `recall@5` sits below 0.90 for reasons that survive a `ts_rank_cd` weight change and
  a reranker, or
- golden cases whose answer is in a second chunk of a long document and which fail today (the golden
  set already names such cases; they pass, which is the evidence against).

Acceptance requires a measurement in `docs/measurements/`: same golden set, same embedder, same
reranker, `CONTEXTUAL_RETRIEVAL=true` versus false, with the command, the environment, and the commit.

## How to run the experiment when the time comes

```bash
CONTEXTUAL_RETRIEVAL=true make ingest        # one completion per chunk, prompt docs/prompts/context/v1.md
make eval-retrieval                          # recall@5, mrr, leak_rate on the same golden set
```

The comparison is only honest if both runs use the same embedder and the same golden set. Changing
the embedder and the context in one step measures nothing: the delta cannot be attributed.

## Measured 2026-10-24

The experiment was finally run at commit `65fc273` on the 137-case set, one ingest each way, same
embedder (`qwen/qwen3-embedding-8b`, dim 1024), same reranker (`nvidia/nemotron-3.5-rerank-8b:free`),
same provider conditions within the same hour:

| arm | `recall_at_5` | `mrr` | artifact |
|---|---|---|---|
| plain index | 0.984 | 0.944 | `docs/measurements/2026-10-24-eval-retrieval-arm-plain.md` |
| `contextual:v1` | 1.000 | 0.919 | `docs/measurements/2026-10-24-eval-retrieval-arm-contextual-on.md` |

Paired against the contextual arm, the plain index loses `recall` −0.015 with an interval of
[−0.036, +0.000] and gains `rr` +0.023 with [−0.005, +0.052], `p(delta <= 0) = 0.059`.

That is a real trade and not a win: the prefix puts two more documents into the top five and pushes
the first correct document down on average. The recall interval touches zero, the ranking interval
touches zero, and two cases decide the first number. The status stays **proposed**: shipping it
would trade a measurable ranking loss for a recall gain the corpus cannot yet prove.

## Consequences

- `kb_chunks.context` exists in every deployment and defaults to `''`; an index built without the
  pass keeps working and reads its embedding from `text`.
- The ingest path grows one sequential model call per chunk, bounded by the corpus size and paid
  once per reindex.
- The prompt is a versioned file (`docs/prompts/context/v1.md`); a wording change is a new version
  plus a re-measurement, like every other prompt in this repository.
