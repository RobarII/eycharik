# 0012 — No BM25 in the request path, for now

Date: 2026-10-23
Status: accepted

## Context

The lexical branch uses Postgres `to_tsvector` + `ts_rank_cd`; it is not BM25. The obvious
production upgrade is ParadeDB `pg_search`, which adds a real BM25 index to the same database and
keeps ACL predicates in SQL.

The corpus is small (10 documents, 13 chunks), so an improvement was not guaranteed. The rule was
to measure before changing the deployment image.

## Experiment

A sidecar ParadeDB container (`paradedb/paradedb`, Postgres 18, port 5433) ran the same migrations
and corpus. The index:

```sql
CREATE INDEX kb_chunks_bm25_idx ON kb_chunks
USING paradedb (id, (text::pdb.simple('stemmer=russian')))
WITH (key_field='id');
```

The probe added BM25 as a third ranked list to the existing reciprocal rank fusion, on branch
`experiment/bm25` (commit `d54287d`). Retrieval-only golden set, same embedder, no generation:

| retrieval | recall@5 | MRR |
|---|---|---|
| semantic + `ts_rank_cd` (shipped) | 1.000 | 1.000 |
| + BM25 third list | 1.000 | 0.938 |

Measurements: [shipped](../measurements/2026-10-23-eval-retrieval-tsrank-16.md),
[BM25](../measurements/2026-10-23-eval-retrieval-parade-bm25.md). Both PASS the gate; MRR is the
metric that moved.

The BM25 list displaced the right document in `guest-photo-permission` (RR 1.00 -> 0.25). With 13
chunks, document frequencies are close to meaningless: one chunk is 7.7% of the corpus, so the IDF
term swings the fusion instead of informing it.

## Decision

Keep the shipped two-list fusion: dense vectors + Russian `ts_rank_cd`, then the cross-encoder
reranker. Do not enable ParadeDB in production yet.

The experiment stays on `experiment/bm25`; it is not merged. Revisit when all three are true:

1. the corpus is large enough for stable document frequencies (hundreds of chunks, not tens);
2. a hard negative set exists — acronyms, document numbers, near-duplicate policies;
3. the golden set shows a retrieval failure that `ts_rank_cd` cannot fix.

Then rerun the branch on the larger corpus and decide from MRR and recall, not from the label
"BM25".

## Consequences

- The deployment stays on `pgvector/pgvector:pg16`: fewer moving parts, no extension build, no
  Postgres major-version jump.
- The lexical branch remains weaker on morphology than a stemmed BM25 index; the reranker covers
  the gap on the current corpus.
- If a future corpus justifies BM25, ParadeDB is the first candidate: same SQL, same ACL, no second
  service. Elasticsearch would need an outbox sync and a new failure domain.
- The fresh-database migration fix from the same session is independent of this decision and stays:
  the initial revision builds `Base.metadata`, so later revisions must not assume their columns are
  absent.
