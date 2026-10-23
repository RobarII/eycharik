# Local preview

`npm run preview:demo` starts Vite with a dev-only API on `/admin/api/*`, so the cabinet can be
reviewed without PostgreSQL or a model provider.

- The fixtures mirror the cohort described in `docs/product/demo-script.md`.
- Tokens: `dev-recruiter-token` (recruiter `rec-1`) and `dev-hr-token` (HR, unscoped).
- The plugin uses `apply: "serve"` and is imported only from `vite.config.ts`; `npm run build`
  never ships it.
- This is a design review tool, not evidence of data quality. The production cabinet still reads
  the API in `docs/contracts/admin-api.md`.
