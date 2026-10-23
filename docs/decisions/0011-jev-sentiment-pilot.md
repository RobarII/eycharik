# 0011 — Jev as an optional sentiment classifier, off by default

Date: 2026-10-23
Status: proposed — code shipped behind a flag, live comparison blocked on a key

## Context

The risk radar reads one free-text survey answer and must return a tone, up to three topic tags,
and a confidence. Two implementations exist today:

- the versioned chat prompt `docs/prompts/sentiment/v1.md` on the answer model;
- `keyword_signal()` in `core/risk.py`, the deterministic fallback.

TypeSafe Jev is not a chat model. It takes one `state` and a map of typed questions and returns
probabilities (`noul` for yes/no, `choice` with a full distribution). That matches the classifier's
contract better than a chat completion: the output is already a distribution, the prompt is a
rubric, and the price is per input token only.

## Decision

Add Jev as a third implementation behind the existing `SentimentAnalysis` port:

- `SENTIMENT_PROVIDER=jev` selects it; the default stays `prompt`;
- the rubric is a versioned file, `docs/prompts/sentiment-jev/v1.yaml`. A wording change is a new
  version, not an edit;
- parsing is strict: every noul answer present, probabilities cover the declared options, sum to 1,
  and the chosen sentiment is the most probable one. A malformed answer is a format error, not a
  guess;
- any transport or format failure degrades to `keyword_signal()` and writes `sentiment_fallback`
  with `provider="jev"`, so a quiet week is distinguishable from a broken classifier;
- the process refuses to start with `SENTIMENT_PROVIDER=jev` and no `JEV_API_KEY`.

The risk level, tags-to-signal mapping, and escalation stay in `core/risk.py`. Jev only labels.

## Measured

The labeled set is `docs/evals/sentiment.yaml`: 16 free-text answers, a tone, and the tags a
recruiter would route.

| provider | sentiment accuracy | tag precision | tag recall | fallback rate | p95 |
|---|---|---|---|---|---|
| keyword baseline | 0.375 | 0.850 | 0.739 | 0.000 | <1 ms |
| prompt, `openai/gpt-4.1-mini` | 0.875 | 0.808 | 0.913 | 0.062 | 2 128 ms |

Files: `docs/measurements/2026-10-23-sentiment-keyword-baseline.md` and
`docs/measurements/2026-10-23-sentiment-prompt-gpt-4.1-mini.md`. Same command
(`make eval-sentiment PROVIDER=...`), same environment, same commit recorded in each file.

The Jev row is deliberately absent: no `JEV_API_KEY` exists in this environment, and a number
without a run is worse than no number. The adapter is covered by unit tests against a mocked
endpoint, not by a quality claim.

## Consequences

- The keyword classifier is a real fallback, but its 0.375 tone accuracy is why the model is the
  default: keywords see a crisis, not "руководитель не отвечает".
- A Jev adoption decision needs the same table filled from a live run. The runner is ready:
  `make eval-sentiment PROVIDER=jev`, then compare accuracy, tag recall, latency, and price.
- One more vendor is a failure mode. ADR 0010 keeps one vendor for answers, embeddings, and
  rerank; Jev is a classifier, not a second answer path, and the flag defaults to off.
- The prompt provider costs one chat call per answer; Jev would cost input tokens only. The price
  difference is not a reason to adopt before the quality difference is measured.

## Alternatives

- Replace the prompt classifier now — rejected: no key, no Russian measurement, and the pilot's
  gates already pass.
- Skip the adapter until a key exists — rejected: the rubric and the strict parser are the risky
  part, and they are testable without the vendor.
- Use Jev for citation support in the answer eval — deferred: the same keyless blocker, and the
  answer eval already has a deterministic citation check.
