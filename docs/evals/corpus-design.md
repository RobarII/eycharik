# Retrieval corpus: how it is built and what it can prove

`knowledge/` is the only thing the assistant may answer from. For retrieval numbers to mean
something, the corpus has to be able to make retrieval fail. This page records the properties the
corpus is built to have, so a later reader can tell a real regression from a corpus that stopped
being a test.

## Why the corpus is a test fixture, not just content

A corpus of one document per topic gives `recall@5 = 1.0` for free: every question has exactly one
plausible target. That measures nothing. The corpus is therefore built as clusters of competing
documents, with three kinds of deliberate traps:

| Trap | Why it exists | Where to look |
|---|---|---|
| Near-duplicate policies | two documents answer almost the same question with different numbers, so a lexical or vector match is not enough | `hr/leave-policy` (28 days) next to `hr/leave-policy-2025` (24 days) |
| Section-level ambiguity | the right answer sits in the second or third chunk, while the first chunk shares the question's keywords | `hr/benefits-dms`, `it/security`, `company/org-structure` |
| Audience and validity edges | a document exists, is relevant, and must still not be retrieved: `hr_only`, `dept:*`, expired edition, `draft` | `hr/salary-bands`, `sales/*`, `production/*`, `hr/benefits-dms-2027` |

Golden cases cover the same three axes; `expect_absent_docs` and `leak_rate` exist because a leak is
not a recall gap. `apps/api/tests/test_golden.py` enforces two invariants: every case names a
document that exists, and every document has at least one case.

## Shape of the corpus

Numbers are produced by `make ingest`, which prints `indexed N documents, M chunks`:

| Measure | Value | Note |
|---|---|---|
| documents | 69 active + 1 draft | draft is validated but never indexed |
| chunks | 78 | `max_chars=1200`, `overlap_chars=200` |
| multi-chunk documents | 8 | the chunking and contextual-retrieval surface |
| audience split | `all` 61, `hr_only` 2, `dept:it` 2, `dept:sales` 5, `dept:production` 4 | ACL cases need competitors, not one token document |
| golden cases | 132 | one or more per document |

## Honest limits

- **78 chunks is not "hundreds".** ADR 0012 asks for a corpus large enough for stable document
  frequencies before a BM25 verdict means anything. At 78 chunks a BM25 result is a probe, not a
  decision, and a measurement must say so.
- **The same author wrote the corpus and the questions.** Questions are phrased from a new hire's
  intent rather than from document wording, but the author knew the answer when writing the
  question. Recall numbers on this set lean optimistic; the caveat travels in the measurement note.
- **The company facts are synthetic.** Names, mailboxes, and every number here are invented for the
  pilot; they are consistent with each other, not with a real POLYPLASTIC policy. Nothing in
  `knowledge/` may be shown to an employee as a real rule until the owner replaces the text.
- **Coverage is not quality.** A case per document proves the document is reachable, not that a
  good answer was given. That is what `answer_contains` and `citation_support` are for, and both
  need a generated answer.
