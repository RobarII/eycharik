# 0022 — A knowledge upload is accepted, not indexed, in the request

Date: 2026-10-25
Status: accepted
Supersedes: 0014 (partially: the markdown upload no longer calls the embedder in the request path)

## Context

Markdown upload validated the frontmatter and then called `ingest_document` and the embedding
provider inside the HTTP request. That made the request hold a database transaction open across a
network call, tied the admin API to the embedder, and made the API container contain a model that
the route was not supposed to own. The file upload already did the right thing: store, enqueue,
answer `202`, let the worker index.

## Decision

1. `POST /admin/api/knowledge` validates the frontmatter, stores the bytes by SHA-256, inserts a
   `queued` extraction row, and enqueues `index_document` in one transaction.
2. It answers `202 Accepted` with `{"content_hash", "status": "queued"}`.
3. The worker validates the stored text again and writes the chunks. The cabinet polls
   `GET /admin/api/knowledge/files/{content_hash}`.
4. `SubmitKnowledge` depends on `KnowledgeSubmitter`, not on `Database`, `PostgresKnowledgeWriter`,
   or `Embedder`. The API container therefore has no embedder at all.

## Consequences

- The request is bounded by validation and one insert; a slow provider cannot time out an upload.
- A repeated upload of the same bytes and profile adds no second job (`queued=false` internally;
  the route still reports `queued` and the poll resolves immediately).
- The admin API contract changes from `201 {id,title,chunks}` to `202 {content_hash,status}`; the
  cabinet polls, as it already does for files.
- An invalid document is rejected before storage when it can be, and by the worker with a
  `rejected` row when the stored bytes disagree with the frontmatter.
