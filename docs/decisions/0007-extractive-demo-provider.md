# 0007: An extractive provider for offline demos

Status: accepted. Date: 2026-10-23.

## Context

The demo must run without a model key: the venue network may block the provider, the key may not be
issued yet, and a judge should be able to clone the repository and see a cited answer. At the same
time the pipeline under test is not the model — it is retrieval, prompt rendering, citation
validation, grounding, escalation, audit, and the cabinet.

## Decision

Add `LLM_PROVIDER=extractive`, a deterministic provider that reads the same rendered prompt the real
model receives, picks the fragment with the largest term overlap with the question, quotes its best
sentences, and returns the same JSON contract with a citation. It refuses personal questions with
`restricted`, prompt injection with `out_of_scope`, and empty retrieval with `no_sources`.

`Settings` rejects `extractive` when `ENVIRONMENT=production`. It is not a language model: it cannot
paraphrase, and its confidence is a heuristic. It exists to exercise the pipeline, never to serve a
newcomer in production.

The golden set runs against it, so the offline path is measured by the same gate as the online one.
Its completion reports zero latency and zero cost by construction: the eval table then measures
retrieval, grounding, and escalation, not model speed or spend.

## Consequences

- The demo needs no provider key and no network; `make eval` works on a laptop.
- A regression in retrieval, citation validation, or escalation shows up offline.
- The provider can over-answer when a document mentions the question's words; the golden set and
  the personal-question markers are the guard.
- Two LLM paths to maintain. The interface is one method, and the provider is under 150 lines.

## Alternatives

A recorded fixture of model answers — rejected: it does not exercise the prompt or retrieval for the
judge's own question. A local open model — rejected: a multi-gigabyte dependency for a demo, and its
quality would still be untested. Running only with a provider key — rejected: the demo must not
depend on the venue's network.
