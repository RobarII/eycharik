# MAX onboarding assistant

AI assistant for employee onboarding in the MAX messenger: onboarding scenarios for newcomers,
a recruiter cockpit, and a retrieval-grounded assistant over the company knowledge base.

Built for the "AI assistant in MAX" case (ООО «Группа ПОЛИПЛАСТИК»).

## Map

| Path | What | Mutable |
|---|---|---|
| `docs/` | architecture, contracts, decisions, runbooks, evals | yes |
| `knowledge/` | non-public company corpus served to the assistant | yes, with owner review |
| `apps/api/` | the service: webhook gateway, scenario engine, RAG, admin API | yes |
| `apps/admin/` | recruiter cockpit | yes |
| `evals/` | golden set runner and reports | yes |
| `infra/` | compose file, database init, tunnel notes | yes |

## Start here

| Question | File |
|---|---|
| What are we building and why? | `docs/architecture.md` |
| How do I work in this repository? | `AGENTS.md` |
| Where does a fact live? | `docs/README.md` |
| What is the bot allowed to answer? | `docs/product/answer-policy.md` |

## Quick commands

```bash
make install     # create the virtual environment
make check       # lint, types, unit tests
make eval        # golden-set retrieval and answer quality
make up          # postgres + api + admin in docker
make dev         # api with reload against local postgres
```

## Status

Skeleton and contracts first, then the vertical slice. Nothing here claims a measurement without
`docs/measurements/`; nothing claims a deployment without `docs/runbooks/`.
