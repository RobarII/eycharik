# Risk radar

The assistant does not only answer questions. Every free-text answer in a survey passes through a
classifier, and the result becomes a signal the recruiter can act on before the employee writes a
resignation letter.

## Pipeline

```
answer text ──▶ sentiment classifier ──▶ signals ──▶ risk rules ──▶ escalation │ digest
                 (prompt, versioned)     (core)      (core)         (worker)    (weekly)
```

Two layers, on purpose:

1. **Classifier** — `docs/prompts/sentiment/v1.md`, one call per free-text answer, JSON per
   `docs/contracts/sentiment.schema.json`. It labels sentiment, topics, confidence and a short
   reason. It never decides about a person.
2. **Rules** — `apps/api/onboarding/core/risk.py`. Pure functions over signals. Deterministic,
   testable, explainable to HR. The same rules run on the keyword fallback, so a classifier outage
   degrades the precision, not the safety net.

## Signals

| Source | Signal |
|---|---|
| scale answer below `low_threshold` | score and threshold, no words |
| free-text answer | sentiment, up to three tags, confidence |
| crisis wording (`увольн`, `конфликт`, `буллинг`, `зарплат` …) | keyword fallback and a hard floor under risk |

Tags: `access`, `manager`, `colleagues`, `workload`, `clarity`, `hr`, `it`, `integration`, `other`.

## Rules

| Condition | Level | Action |
|---|---|---|
| negative answer with a tag | `high` | escalate to the recruiter |
| confident complaint (`confidence >= 0.5`) and a scale deficit | `high` | escalate |
| crisis wording regardless of confidence | `high` | escalate |
| score below the threshold, no words | `medium` | weekly digest |
| classifier confidence below `0.5` | not worse than `medium` | digest, never a false alarm |

A single number cannot escalate on its own: a person may simply rate a day as a six out of ten.
Escalation needs either words or a combination of signals.

## What the recruiter sees

- `risk_assessed` and `risk_escalated` in the audit log, with step, level, score, tags and reasons.
- The run card in the cockpit shows the current level and the answers behind it.
- The weekly digest groups employees by level and tag, so a recruiter sees "three people cannot get
  access" before reading three separate cards.

## Refusals

The classifier sees personal text, so:

- the reason field is bounded to 200 characters and must not repeat names or long quotes;
- signals are stored with the run, not in a separate profile;
- the prompt is a versioned file, and a change needs an eval run in `docs/measurements/`.

## Failure modes

| Failure | Behaviour |
|---|---|
| provider timeout or invalid JSON | keyword fallback, `risk_assessed` records `fallback` |
| classifier says `low` but crisis words are present | keyword floor raises the level |
| confidence below `0.5` | capped at `medium`, goes to the digest |
| repeated escalation for one run | worker sends at most one message per level per run |

## Which classifier

Two providers implement the same port. The versioned chat prompt is the default; the keyword
classifier is the fallback and the offline baseline. A third option, TypeSafe Jev, ships behind
`SENTIMENT_PROVIDER=jev` with its own rubric and the same strict parsing; it is not the default
because its quality on Russian answers is not measured yet (ADR 0011). Whatever the provider, the
level, tags-to-signal mapping, and escalation stay in `core/risk.py`, where a test can pin them.
