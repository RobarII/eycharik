# 0021 — Model identity has one home: the profile

Date: 2026-10-25
Status: accepted
Supersedes: 0013 (partially: removes the environment-built fallback profile), 0020 (partially:
removes `JEV_MODEL` and the classifier's env fallback)

## Context

ADR 0013 put model identity, envelope, and prices in `apps/api/model-profiles/<role>/<name>.yaml`.
The adapters still kept an escape hatch: when no profile was named, they built an in-memory `env`
profile from `LLM_MODEL`, `EMBED_MODEL`, or `JEV_MODEL`. That fallback was convenient in tests and
wrong in production:

- a deployment could run a model that no committed profile describes, so an eval result could not
  be reproduced from the repository;
- the vendor default (`gpt-4o-mini`, `Embeddings`, `jev-1.13.0`) lived in `Settings`, which is
  exactly the kind of hidden default that makes a "profile-only" rule untrue;
- `LLM_MODEL` and `LLM_PROFILE` could disagree, and nothing said which one won.

## Decision

1. An answer model is selected by `LLM_PROFILE`. Except for `LLM_PROVIDER=extractive`, a missing
   profile is a startup error.
2. An embedder is selected by `EMBED_PROFILE`. `EMBED_PROVIDER=hashing` is the one exception: it is
   a local, deterministic test embedder whose model is not a vendor identity.
3. A classifier is selected by `CLASSIFY_PROFILE`. A missing profile is a startup error.
4. `LLM_MODEL`, `EMBED_MODEL`, and `JEV_MODEL` do not exist. The answer, embedding, and
   classifier model names have exactly one home: their profile.
5. Envelope and price overrides (`LLM_MAX_TOKENS`, `JEV_TIMEOUT_S`, ...) remain: they are
   experiment knobs applied on top of the selected profile, never a substitute for one.

## Consequences

- A process refuses to start when the environment names no model profile, instead of silently
  calling a vendor default.
- Tests that need a model set `LLM_PROFILE`/`EMBED_PROFILE`/`CLASSIFY_PROFILE` like production.
- `.env.example` no longer advertises model names; it names profile files.
- The eval runner and the worker still share one factory per role, so they cannot select
  differently.
