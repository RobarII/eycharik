# 0004: Prompts are versioned files

Status: accepted. Date: 2026-10-23.

## Context

Tone and refusal rules are product behaviour. A prompt edited inside a Python string is invisible
in review, impossible to diff, and cannot be rolled back independently of a deploy. Quality
regressions are then blamed on the model.

## Decision

Prompts live in `docs/prompts/<name>/<version>.md` with a `<version>.meta.yaml` that records the
model, temperature, eval result, and the version it supersedes. Code loads by explicit version.
Every trace records the prompt version.

## Consequences

- A prompt change is a reviewable diff plus an eval run.
- Rolling back is a one-line version change.
- A version is immutable; improvements are a new file.
- The meta file must not claim a score that is not in `docs/measurements/`.

## Alternatives

Prompt in code — rejected. Prompt in a database edited by HR — rejected for now: no review, no
diff, no eval gate. It becomes viable after the eval harness is trusted, with the same rules.
