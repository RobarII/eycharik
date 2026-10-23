# Recruiter cabinet

React 18 + TypeScript + Vite + TanStack Query. No router library: the URL hash is the router.
No component library: `styles.css` holds the tokens and the few primitives the cabinet needs.

Read [`README.md`](README.md) before the first change: screens, tokens and their scopes, the
knowledge document schema, the preview mode, and the known limits.

## Rules

1. Writes are the four the contract allows: resolve a question, publish a knowledge document,
   upload a PDF or a deck, and offboard an employee. The cabinet calls `/admin/api/*` and never MAX;
   a reply is queued through the outbox in the same transaction that closes the question.
2. The token never lives in the page. It is exchanged on the gate for an HttpOnly cookie
   (`docs/decisions/0018`) and is not readable by script afterwards. A `401` returns to the gate.
   What a role may see is decided by `capabilities` from `GET /admin/api/me`, never by the client.
3. Every list shows an explicit empty state and an explicit error with a retry. "Nothing" and
   "failed" must never look the same.
4. Timestamps arrive as UTC ISO strings and are formatted for the reader, never recomputed.
5. A question always shows whose it is. A queue without names is a queue nobody works.
6. Accessibility is not decoration: real buttons, labels, `aria-live` counts, focus rings,
   reduced-motion support. `npm run e2e` runs axe on every screen; a `critical` or `serious`
   violation fails it.
7. A contrast fix is not a taste fix: small text needs 4.5:1, and `prefers-reduced-motion` must
   turn animations off, not just shorten them.

## Commands

```bash
npm install
npm run dev          # :5173, proxies /admin/api to :8000
npm run preview:demo # :5173, dev-only demo API with the documented cohort
npm run build        # tsc -b + vite build
npm run typecheck
npm run lint         # eslint: typescript, hooks, jsx-a11y
npm run test         # vitest: routing, lists, write flows, format
npm run e2e          # playwright + axe against the demo API (make admin-e2e)
```

## API

`docs/contracts/admin-api.md` is the contract. If a field is missing, change the contract and the
server first; do not guess a shape in the client.
