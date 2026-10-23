# 0001: Functional core, imperative shell

Status: accepted. Date: 2026-10-23.

## Context

Scenario transitions, chunk ranking, and grounding checks are the parts that fail silently: a wrong
transition looks like a working bot, an ungrounded answer looks like a confident one. They also
change most often. Anything that needs a database or a model to test is expensive to verify and
slow to iterate on.

## Decision

`apps/api/onboarding/core/` is pure. It imports only the standard library and sibling core
modules. Time, identifiers, model output, and retrieved chunks arrive as arguments. Every effect
lives in `app/` behind a port declared in `ports.py`.

## Consequences

- `core/` is tested with plain unit tests: no database, no network, no patching.
- The same transition code runs in tests, in the worker, and in the eval harness.
- An effect added to `core/` fails code review, `ruff` import rules, and `mypy` strictness.
- More plumbing: the worker must load and persist around every pure call. Accepted.

## Alternatives

Hexagonal architecture with a framework (dependency-injector, punq) — rejected: one extra concept
for no testability gain. Testing through the web layer — rejected: slow and it hides which rule
failed.
