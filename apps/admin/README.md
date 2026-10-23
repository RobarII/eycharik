# Recruiter cabinet (web)

The human side of the MAX onboarding assistant. React 18 + TypeScript + Vite + TanStack Query.
The cabinet reads the admin API, shows where each newcomer is, which answers need a person, and lets
HR index a knowledge document. It never talks to MAX and it never sends chat messages.

## Run

```bash
npm install
npm run dev          # :5173, proxies /admin/api to http://localhost:8000
npm run preview:demo # :5173, dev-only API with the documented cohort, no database
npm run typecheck    # tsc -b --noEmit
npm run build        # tsc -b + vite build
```

`npm run dev` is the real frontend: it needs the API and its PostgreSQL. `npm run preview:demo` is a
design/review tool; see [Preview mode](#preview-mode).

## Routes

The URL hash is the router; there is no router dependency.

| Hash | Screen | Purpose |
|---|---|---|
| `#/overview` | Overview | Seven-day snapshot, risks, queue, topics, new hires |
| `#/runs` | Employees | Active and completed runs, search, filters |
| `#/run/<run_id>` | Employee detail | Step, facts, questions, audit timeline |
| `#/questions` | Questions | Unanswered and answered queue, reasons, citations |
| `#/risk` | Risks | Counters, weekly digest, risk topics |
| `#/knowledge` | Knowledge | Upload a markdown document, list indexed documents |

The default route is `#/overview`. The token gate is shown before any route when no token is stored.

## Authentication and tokens

There is no session and no cookie. Every API request carries a bearer token:

```http
Authorization: Bearer <token>
```

The server maps tokens to `(role, subject)` from `ADMIN_TOKENS`, a comma-separated list of
`token:role:subject` entries:

```dotenv
ADMIN_TOKENS=dev-recruiter-token:recruiter:rec-1,dev-hr-token:hr_admin:hr-1
```

| Role | Subject | Scope |
|---|---|---|
| `recruiter` | recruiter id, e.g. `rec-1` | Employees whose `recruiter_id` equals the subject |
| `hr_admin` | HR identity, e.g. `hr-1` | Every employee, every question, every knowledge document |

The current token parser (`Settings.admin_principals`) accepts exactly `recruiter` and `hr_admin`.
`manager` appears in the API contract and in `AdminPrincipal.is_manager`, but a manager token makes
the process refuse to start today. Do not issue one until the parser, the server tests, and this
table agree.

Status codes the frontend relies on:

| Code | Meaning | Frontend behaviour |
|---|---|---|
| `401` | Missing or unknown token | Clear `onboarding.admin.token`, show the gate |
| `403` | Role may not perform the mutation, e.g. recruiter uploads knowledge | Show the API `detail`, keep the session |
| `404` | Run does not exist **or** is outside the caller's scope | Show the detail; never guess that another recruiter's employee exists |

A run outside the scope is deliberately `404`, not `403`.

### Why the preview has two tokens

They are not two factors for one HR. They are two different scopes:

- `dev-recruiter-token` — role `recruiter`, subject `rec-1`: sees only Anna and Peter.
- `dev-hr-token` — role `hr_admin`: sees Maria as well, plus the `hr_only` document.

The second token exists to prove that scoping happens in SQL, not in the UI: sign in as the
recruiter and Maria disappears. For ordinary HR work one token is enough.

### Production tokens

Issue one token per person, not one shared token per role. A recruiter's subject must match
`employees.recruiter_id`; an HR token is unscoped. Use long random values, rotate them with a
deploy, and keep them in the server environment. Example generation:

```bash
openssl rand -hex 32
```

The browser stores the token in `localStorage` under `onboarding.admin.token` and nowhere else.
A `401` clears it. The token is never put in a URL, a log line, or a build artifact.

### Token vs MAX bot token

Do not confuse the two:

| Variable | Who uses it | Where it lives |
|---|---|---|
| `ADMIN_TOKENS` | recruiters and HR reading this cabinet | server env and the user's browser |
| `MAX_BOT_TOKEN` | the API/worker sending messages to MAX | server env only, never the browser |
| `MAX_WEBHOOK_SECRET` | MAX proving a webhook call | server env only |

The frontend has no MAX credentials at all.

## API surface

The contract of record is [`docs/contracts/admin-api.md`](../../docs/contracts/admin-api.md). If a
screen needs a field the contract does not have, change the contract and the server first; never
guess a shape in the client.

| Method and path | Returns |
|---|---|
| `GET /admin/api/runs?limit=50` | `{ items: RunSummary[] }`, newest activity first |
| `GET /admin/api/runs/{run_id}` | `RunDetail`: summary + scenario, tone, step message, events, questions |
| `GET /admin/api/questions?status=unanswered&limit=50` | `{ items: Question[] }`; status is `unanswered`, `answered`, `all` |
| `GET /admin/api/analytics/overview` | Seven-day counters and `top_tags` |
| `GET /admin/api/digest/weekly?days=7` | `{ items: DigestItem[], since }` |
| `GET /admin/api/knowledge` | `{ items: KnowledgeDocument[] }` |
| `POST /admin/api/knowledge` | `201 { id, title, chunks }`; `hr_admin` only |
| `GET /healthz`, `/readyz` | Liveness/readiness, no auth |

`limit` is bounded to `1..200`. There is no cursor pagination: the cabinet asks for the newest 50
and the cohort is one hire batch. Add a cursor before raising the cap.

Timestamps are UTC ISO 8601 strings. `src/format.ts` formats them for the reader; the client never
recomputes them.

## Knowledge documents

This is the only mutation available in the cabinet today. HR uploads markdown with YAML
frontmatter; the API validates it, chunks it, and indexes it in the same request.

### Frontmatter

The schema is [`docs/contracts/doc.schema.json`](../../docs/contracts/doc.schema.json). Unknown
fields are rejected (`additionalProperties: false`).

| Field | Required | Type | Values |
|---|---|---|---|
| `id` | yes | string | `^[a-z0-9][a-z0-9/_-]*$`, e.g. `hr/leave-policy` |
| `title` | yes | string | Human title, minimum one character |
| `type` | yes | string | Always `knowledge` |
| `status` | yes | string | `draft`, `active`, `deprecated` |
| `owner` | yes | string | `^[a-z][a-z0-9_-]*$`, e.g. `hr`, `it`; a team slug, not a person |
| `audience` | yes | string[] | Non-empty, unique; each item is `all`, `hr_only`, or `dept:<slug>` |
| `valid_from` | yes | date | `YYYY-MM-DD`; the first day the document applies |
| `valid_to` | no | date or null | Last day the document applies; `null` means no end date |
| `source_of_truth` | no | string | Link or reference to the canonical document |
| `related` | no | string[] | Related document ids |

### What the values mean

`audience` is enforced twice: in the retrieval SQL and in the admin query. The bot must never see a
document outside the employee's audience.

| Audience | Who receives it |
|---|---|
| `all` | Every employee |
| `dept:<slug>` | Employees whose directory audience contains the same department slug |
| `hr_only` | HR only; the bot must never use it in an answer |

Use the directory's audience slug, not the Russian display name, in `dept:` values. Check the
employee's `audience` in the directory before inventing one.

`status` controls indexing:

- `active` — loaded from `knowledge/`, indexed by upload, and eligible for retrieval.
- `draft` and `deprecated` — valid in the schema, skipped by corpus loading, and rejected by the
  upload endpoint (it requires `active`). Use them in the corpus for documents that are not ready.

Validity is a retrieval predicate: `valid_from <= today` and (`valid_to is null` or
`valid_to >= today`). A future `valid_from` is indexed but not used yet.

### Upload contract

```http
POST /admin/api/knowledge
Content-Type: application/json
Authorization: Bearer <hr_admin token>

{"text": "---\nid: hr/sport-compensation\ntitle: Компенсация спорта\ntype: knowledge\nstatus: active\nowner: hr\naudience: [all]\nvalid_from: 2026-10-01\n---\n\n## Спорт\n\nКомпания компенсирует часть абонемента."}
```

```json
{"id": "hr/sport-compensation", "title": "Компенсация спорта", "chunks": 1}
```

- `201` means the document is indexed; the next answer can cite it as `hr/sport-compensation#0`.
- `422` returns the exact failing field, e.g.
  `upload: owner: 'HR' does not match '^[a-z][a-z0-9_-]*$'`.
- `403` means the caller is not `hr_admin`; the cabinet keeps the session and shows the detail.
- A success is audited as `knowledge_ingested` with the document id, chunk count, and subject.
- Chunking is deterministic and server-side; the response reports the number of chunks.

### Preview knowledge values

The preview fixtures mirror the documented cohort and use four documents:

| `id` | `audience` | `owner` | Visible to recruiter |
|---|---|---|---|
| `hr/leave-policy` | `all` | `hr` | yes |
| `hr/benefits-dms` | `all` | `hr` | yes |
| `it/access-and-equipment` | `all` | `it` | yes |
| `hr/sick-leave` | `hr_only` | `hr` | no |

The real corpus lives in `knowledge/` and includes company policies, HR policies, and IT access
instructions. Every file there also carries this frontmatter.

### Known role-scoping gap

`docs/product/roles.md` says only `hr_admin` may read `hr_only` documents. The current
`GET /admin/api/knowledge` returns active documents without filtering by the caller's role. The
preview filters them, but the real endpoint must be scoped before production. Until then, do not
treat the knowledge list as an access control boundary.

## Preview mode

`npm run preview:demo` starts Vite with a dev-only API on `/admin/api/*`, so the cabinet can be
reviewed without PostgreSQL or a model provider.

- The plugin is [`preview/plugin.ts`](preview/plugin.ts); the fixtures are
  [`preview/data.ts`](preview/data.ts); the short note is [`preview/README.md`](preview/README.md).
- The fixtures mirror the cohort in `docs/product/demo-script.md`, not production data.
- Tokens: `dev-recruiter-token` (recruiter `rec-1`) and `dev-hr-token` (HR, unscoped).
- Upload in preview changes the in-memory document list only. It does not reindex a vector store and
  the bot cannot answer from it. In the real API the upload is indexed in the request.
- The plugin uses `apply: "serve"` and is imported only by `vite.config.ts`; `npm run build` never
  ships it.
- This mode is for design and interaction review. It is not evidence of retrieval quality, model
  quality, or production readiness.

`npm run dev` is the production-shaped setup: Vite proxies `/admin/api` to
`VITE_PROXY_TARGET` (default `http://localhost:8000`). The Docker image serves the built `dist/`
through nginx, which proxies `/admin/api` to the `api` service.

## UI system

The cabinet has no component library and no chart library. `src/styles.css` owns the tokens and the
few primitives; icons are inline SVG in `src/components/Icons.tsx`.

| Token | Value | Use |
|---|---|---|
| `--bg` | `#FAF7F2` | Page background |
| `--surface` | `#FFFFFF` | Cards, sidebar, controls |
| `--accent` | `#C56A43` | Accent fills, active indicators, primary button |
| `--accent-deep` | `#9D4F2E` | Text-safe accent, gate panel |
| `--accent-soft` | `#F5E4D9` | Highlight, active nav, high-risk card |
| `--ink` | `#292524` | Primary text |
| `--ink-2` | `#57534E` | Secondary text |
| `--muted` | `#857C74` | Metadata |
| `--line` | `#EEE7DF` | Borders |

Rules of the system:

- Cards are white on cream, with one subtle border and a very light shadow. No gradients or
  decorative glass; the sticky topbar uses a light blur only for legibility.
- Numbers are tabular. Headings use tighter letter spacing; body text stays at 1.5 line height.
- Charts are CSS bars and a segmented progress rail; no canvas, no chart dependency.
- The sidebar is 248 px; below 1024 px it becomes an icon rail; below 760 px it becomes a fixed
  bottom navigation with the same five sections.
- On mobile, long rows (name + reason pill + time) reflow to a two-line grid, and the body clips
  horizontal overflow. This keeps the layout viewport at the device width and the fixed navigation
  on screen.
- Main lists have three distinct states: loading skeleton, explicit empty state, and an error with
  a retry. "Nothing" and "failed" never look the same.
- The gate is the only full-screen screen; the token is never prefilled.
- The topbar has one refresh action, plus a logout icon on narrow screens. There is no "live data"
  label and no footer with environment notes; the cabinet should look the same in demo and
  production.

Accessibility is part of the definition of done: a skip link, real buttons and labels, `aria-current`
on navigation, `aria-live` on counts, visible focus rings, and `prefers-reduced-motion` support.

## File map

| Path | Responsibility |
|---|---|
| `src/App.tsx` | Shell, hash router, token state, navigation badge, global refresh |
| `src/api.ts` | Fetch wrapper, bearer header, `Unauthorized`, query functions |
| `src/types.ts` | API response types; mirrors the contract |
| `src/format.ts` | Dates, Russian plurals, reason/event/step/tag labels, initials |
| `src/styles.css` | Tokens, layout, components, responsive rules |
| `src/components/Icons.tsx` | Inline SVG icon set and logo mark |
| `src/components/TokenGate.tsx` | Login by token |
| `src/components/Pills.tsx` | Status, answer, reason pills |
| `src/components/Progress.tsx` | Step progress |
| `src/components/States.tsx` | Empty, error, skeleton |
| `src/pages/OverviewPage.tsx` | Dashboard |
| `src/pages/RunsPage.tsx` | Employee list and filters |
| `src/pages/RunDetailPage.tsx` | Employee card and audit timeline |
| `src/pages/QuestionsPage.tsx` | Question queue |
| `src/pages/RiskPage.tsx` | Risk counters and weekly digest |
| `src/pages/KnowledgePage.tsx` | Knowledge upload and list |
| `preview/` | Dev-only API and fixtures; never in a production build |

## Limits and next mutations

- The cabinet is read-only except `POST /admin/api/knowledge`.
- Manual messages to an employee and escalation resolution are not implemented. They are the next
  mutations in the contract; until then the human action happens in MAX and the decision is tracked
  outside the cabinet.
- No cursor pagination. `limit` is capped at 200.
- A `manager` role is reserved in the contract and has an `AdminPrincipal.is_manager` property, but
  the current `ADMIN_TOKENS` parser rejects it. Do not advertise manager access until the server
  accepts and tests it.
- The knowledge list is not role-scoped in the current server; see the gap above.
- No in-app notifications, exports, saved views, or assignment. Those are product decisions that
  need a contract change first.
- UI copy is Russian. Documentation is English, per the workspace rules.

## When changing the frontend

1. Read `docs/contracts/admin-api.md` and the relevant product doc before changing a screen.
2. If a field is missing, change the contract and the server first; do not invent a shape in `types.ts`.
3. Run `npm run typecheck` and `npm run build`.
4. Keep the three list states and the accessibility rules.
5. If the change is a product claim or a measured number, add the command, environment, and commit
   to `docs/measurements/`; the preview is not a measurement.
6. Never add a MAX bot token, provider key, or real admin token to this app.
