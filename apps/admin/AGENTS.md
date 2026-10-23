# Recruiter cabinet

React 18 + TypeScript + Vite + TanStack Query. No router library: the URL hash is the router.
No component library: `styles.css` holds the tokens and the few primitives the cabinet needs.

Read [`README.md`](README.md) before the first change: screens, tokens and their scopes, the
knowledge document schema, the preview mode, and the known limits.

## Rules

1. The cabinet is read-only. It calls `/admin/api/*` with a bearer token and never talks to MAX.
2. The token lives in `localStorage` under `onboarding.admin.token` and nowhere else. A `401`
   clears it and returns to the gate.
3. Every list shows an explicit empty state and an explicit error with a retry. "Nothing" and
   "failed" must never look the same.
4. Timestamps arrive as UTC ISO strings and are formatted for the reader, never recomputed.
5. A question always shows whose it is. A queue without names is a queue nobody works.
6. Accessibility is not decoration: real buttons, labels, `aria-live` counts, focus rings,
   reduced-motion support.

## Commands

```bash
npm install
npm run dev          # :5173, proxies /admin/api to :8000
npm run preview:demo # :5173, dev-only demo API with the documented cohort
npm run build        # tsc -b + vite build
npm run typecheck
```

## API

`docs/contracts/admin-api.md` is the contract. If a field is missing, change the contract and the
server first; do not guess a shape in the client.
