# Documentation index

The single entry point. Every document in `docs/` is listed here; CI fails when a file is missing
from this table. If a question is not answered here, the answer does not exist yet — add the row.

## By question

| Question | File |
|---|---|
| What is the system made of, and how does a message travel through it? | [architecture.md](architecture.md) |
| What did the client actually ask for? | [case/poliplastic-2026.md](case/poliplastic-2026.md) |
| What do the words mean? | [glossary.md](glossary.md) |
| How do we write code, tests, and commits? | [conventions.md](conventions.md) |
| What exactly does the MAX API give us? | [contracts/max-api.md](contracts/max-api.md) |
| What does the recruiter cabinet call, and with what rights? | [contracts/admin-api.md](contracts/admin-api.md) |
| What exactly does the model see? | [prompts/answer/v2.md](prompts/answer/v2.md) (current), [v1](prompts/answer/v1.md) (superseded) |
| What does the assistant answer, and what does it refuse? | [product/answer-policy.md](product/answer-policy.md) |
| What does the sentiment layer return? | [contracts/sentiment.schema.json](contracts/sentiment.schema.json) |
| What are the onboarding scenarios? | [product/scenarios.md](product/scenarios.md) |
| How do I demo this in five minutes? | [product/demo-script.md](product/demo-script.md) |
| Who may see what? | [product/roles.md](product/roles.md) |
| Why is the code split into core and app? | [decisions/0001-functional-core.md](decisions/0001-functional-core.md) |
| Why does the webhook answer before doing work? | [decisions/0002-async-webhook.md](decisions/0002-async-webhook.md) |
| Why hybrid retrieval instead of pure vectors? | [decisions/0003-hybrid-retrieval.md](decisions/0003-hybrid-retrieval.md) |
| Why are prompts files with versions? | [decisions/0004-prompts-as-data.md](decisions/0004-prompts-as-data.md) |
| Why does one Postgres hold state, vectors, and the outbox? | [decisions/0005-single-postgres.md](decisions/0005-single-postgres.md) |
| Why refuse instead of guessing? | [decisions/0006-refuse-over-guess.md](decisions/0006-refuse-over-guess.md) |
| Why is there an offline provider? | [decisions/0007-extractive-demo-provider.md](decisions/0007-extractive-demo-provider.md) |
| How do I deploy? | [runbooks/deploy.md](runbooks/deploy.md) |
| How do I migrate the database? | [runbooks/migrate.md](runbooks/migrate.md) |
| The model provider is down — what now? | [runbooks/llm-outage.md](runbooks/llm-outage.md) |
| Webhooks return 401 — what now? | [runbooks/webhook-auth.md](runbooks/webhook-auth.md) |
| How is answer quality measured? | [evals/README.md](evals/README.md) |
| Where do measured numbers live? | [measurements/TEMPLATE.md](measurements/TEMPLATE.md) |
| Where does a postmortem live? | [incidents/TEMPLATE.md](incidents/TEMPLATE.md) |

## Document classes

| Class | Purpose | Change rule |
|---|---|---|
| `architecture.md`, `glossary.md`, `conventions.md` | normative description of the system | edit in place, keep the anchor headings stable |
| `contracts/` | schemas and API surfaces that code is generated from or validated against | schema first, code second |
| `decisions/` | immutable records of why | never edit an accepted ADR; add a new one |
| `runbooks/` | steps under stress | keep short, imperative, tested in staging |
| `product/` | rules the bot and the cockpit obey | edit with a matching test or eval case |
| `case/` | transcript of the client brief | append corrections with a date; never reword the quotes |
| `evals/` | the quality gate | every new failure mode becomes a case |
| `measurements/`, `incidents/` | evidence | one file per event, never rewritten |

## Frontmatter

Every document under `knowledge/` carries YAML frontmatter validated by
[contracts/doc.schema.json](contracts/doc.schema.json). Documents under `docs/` do not need
frontmatter; the index above is their identifier.
