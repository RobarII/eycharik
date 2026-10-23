# Runbook: an uploaded document did not reach the corpus

Extraction runs in the worker (ADR 0015). A file is stored, queued, extracted, decided, and only
then indexed. Every step leaves a row, so a refusal is diagnosable without logs.

## 1. Where is the file?

```bash
psql "$DATABASE_URL" -c "select id, filename, media_type, size, created_at from kb_files order by created_at desc limit 10"
psql "$DATABASE_URL" -c "select status, reason, engine, route, pages, min_confidence, document_id, updated_at from kb_extractions where content_hash = '<hash>'"
psql "$DATABASE_URL" -c "select id, kind, attempts, last_error from jobs where kind = 'extract_document' order by id desc limit 10"
```

The cabinet shows the same thing: `GET /admin/api/knowledge/files/{hash}`. No row at all means the
job has not run yet; check that the worker is up (`make logs`).

## 2. Read the reason

| `reason` | Meaning | Fix |
|---|---|---|
| `unsupported` | format is not PDF or PPTX, or no reader owns the declared type | convert to PDF |
| `encrypted` | the PDF needs a password | upload a decrypted copy |
| `no_pages` | the parser found no pages: a broken or truncated file | re-export from the source |
| `too_many_pages` | above `EXTRACTION_MAX_PAGES` | split the document, or raise the limit |
| `low_dpi` | the raster is under `quality.min_dpi` | upload the original, not a photo of a printout |
| `blurry` | high-frequency detail under `quality.min_edge_energy` (unset by default) | steady the camera, use the scanner app |
| `unreadable` | the raster is not a decodable image | re-export the page |
| `low_confidence` | a page scored under `acceptance.min_confidence`: glare, a stamp, or handwriting | re-shoot that page, or use a stronger profile |
| `too_short` | the accepted text is under `acceptance.min_chars` | the file is not a document |
| `empty` | every page produced no text | same |

A refusal is not an error: the job completed. Nothing is indexed and nothing is retried, because the
answer would be identical.

## 3. Re-read the same file with a better profile

The cache is keyed by `(content_hash, profile_hash)`, so changing `EXTRACTION_PROFILE` and restarting
the worker re-reads the same bytes without a new upload:

```bash
EXTRACTION_PROFILE=doc-scan uv run python -m onboarding.cli extract --file regulation.pdf
```

That dry run prints the route, the engine, the page count, and the verdict, and touches no database.
If it accepts, switch the worker to the same profile, then enqueue the file again:

```bash
psql "$DATABASE_URL" -c "insert into jobs (kind, payload) values ('extract_document', jsonb_build_object('blob_id','<hash>','filename','regulation.pdf','media_type','application/pdf','metadata','{}'::jsonb))"
```

For a real upload use the cabinet or `curl -F` against `POST /admin/api/knowledge/files` with the
metadata part; an empty `metadata` is rejected by the contract, by design.

## 4. Turn recognition on

Recognition is an optional extra. Without it the `native` profile refuses every scan with
`unsupported` and digital files are unaffected.

```bash
uv sync --extra ocr            # rapidocr + onnxruntime, CPU, no Paddle runtime
EXTRACTION_PROFILE=doc-scan make up
```

The first job downloads nothing: RapidOCR ships PP-OCRv5 weights inside the wheel. Apple Silicon is
supported; no GPU is required or used.

## 5. Recalibrate the gate

Thresholds are provisional until measured. The blur proxy is the mean absolute high-frequency
detail of the raster, and it depends on resolution and ink coverage, so it may only be compared
within one reader and one profile. There is no glare score on purpose: the share of saturated
pixels is ~0.96 on a perfectly clean page, so it would refuse every document.

```bash
make eval-ocr                  # character error rate and refusal correctness on docs/evals/ocr.yaml
```

Change a threshold only with a measurement file in `docs/measurements/` that names the command, the
environment, and the commit. A profile's `fingerprint()` changes with its thresholds, so the cache is
invalidated automatically — no manual purging.

## 6. Bytes are gone after the retention window

`RetentionPurger` deletes `kb_files` rows older than `DATA_RETENTION_DAYS`. The accepted markdown is
already a document in `kb_documents`, so the text survives; only the source bytes are removed. A
cached extraction record without its file cannot be re-read — upload the file again in that case.
