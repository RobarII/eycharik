# Knowledge metadata

There is no separate ACL file. The frontmatter of each document is the single source of truth:

- `audience` — who may retrieve the document: `all`, `dept:<name>`, `hr_only`.
- `valid_from` / `valid_to` — the validity window; expired documents are never retrieved.
- `owner` — who reviews the document; the staleness report groups by owner.
- `status` — `draft` is not indexed, `deprecated` is not indexed, `active` is.

Adding a document means adding a row to the owner's review queue. The ingestion job validates each
file against `docs/contracts/doc.schema.json` and fails the whole batch on one invalid file, so a
half-indexed corpus cannot happen.
