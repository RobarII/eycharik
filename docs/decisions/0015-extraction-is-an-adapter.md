# 0015 — Extraction is an adapter, not a step in the webhook

- Status: accepted
- Date: 2026-10-28
- Supersedes: nothing
- Related: [0001](0001-functional-core.md), [0002](0002-async-webhook.md),
  [0006](0006-refuse-over-guess.md), [0013](0013-model-profiles.md)

## Context

The corpus accepted one format: markdown with frontmatter, written by a human. Every real HR
document is a PDF or a deck, and the recruiters' own files are often scans of paper. "Paste the text
into markdown" is not a workflow a recruiter will follow, and a hand-copied regulation is a document
nobody can trace back to its source.

The obvious shortcut is wrong in three ways:

1. **OCR in the request path.** Recognition costs seconds per page. The webhook already answers
   before doing work ([0002](0002-async-webhook.md)); an upload endpoint that blocks on Paddle or
   ONNX would put a 30-second request in front of a recruiter with a 60-page regulation.
2. **An OCR engine in `core/`.** The functional core has no I/O, no randomness, no clock, and no
   heavy dependencies (`apps/api/tests/test_core_purity.py`). PaddleOCR, OpenCV, and pdfium all
   violate that, and pulling even one of them in makes the pure rules untestable without a model.
3. **Trusting the recognizer.** An OCR engine never says "I am not sure" — it produces confident
   nonsense on a photographed page with glare or a stamp over the text. Text that looks like a
   regulation but is wrong is worse than no document: the assistant answers from it and cites it.
   That is exactly what [0006](0006-refuse-over-guess.md) forbids.

There is a fourth, quieter problem: the engine will change. Today it is PP-OCRv5 over ONNX Runtime,
tomorrow it is PaddleOCR-VL or a hosted service, and the thresholds that decide "good enough" are
facts about the *engine and the language*, not about this codebase.

## Decision

**Extraction is an adapter behind a port. The decision it feeds is a pure function.**

- `onboarding/ports.py` gains `DocumentReader`, `Ocr`, `Extraction`, `BlobStore`, and
  `ExtractionCache`. The central port is result-oriented:

  ```python
  async def extract(content: bytes, ref: DocumentRef,
                    profile: ExtractionProfile) -> ExtractedDocument
  ```

  It returns pages, or a refusal with a reason. It does not raise for a bad document: a refusal is
  a value ([0006](0006-refuse-over-guess.md)).

- `onboarding/core/extraction.py` holds every rule, as pure functions over value objects:
  `refusal` (encryption, no pages), `route` (native text layer or recognition), `assess` (the
  quality gate), `normalize` (typographic repair that never touches a digit), `assemble`,
  `accept`. `core/` imports nothing from `app/`, and `test_core_purity.py` now also forbids
  `paddleocr`, `rapidocr`, `onnxruntime`, `cv2`, `PIL`, `pypdfium2`, and `pptx` there.

- `onboarding/app/knowledge/extract/` holds the adapters, one concern each: `pdf.py` (pdfium text
  layer and rasterization), `pptx.py` (text frames, tables, embedded pictures), `quality.py`
  (high-frequency detail of the raster the engine will actually see), `ocr.py` (one recognizer per
  class; `UnavailableOcr` refuses honestly), `router.py` (sequence the effects, off the event loop
  via `asyncio.to_thread`), `compose.py` (frontmatter plus body), `profiles.py` (read and validate
  the YAML).

- **The engine is a profile, not a code path** ([0013](0013-model-profiles.md)).
  `apps/api/model-profiles/extract/<name>.yaml` is validated against
  [`contracts/extraction-profile.schema.json`](../contracts/extraction-profile.schema.json) at
  startup: `family` (`none|paddle|rapid|tesseract`), `model`, `lang`, `dpi`, `min_text_chars`,
  `quality` thresholds, `acceptance` thresholds. `EXTRACTION_PROFILE` selects one; a broken profile
  stops the process. `family` is turned into a class in exactly one place, the composition root.

- **One job per file.** `POST /admin/api/knowledge/files` validates the metadata against
  `doc.schema.json` (the same contract a committed document obeys), stores the bytes in `kb_files`
  keyed by their SHA-256, and enqueues `extract_document`. The worker extracts, decides, renders
  markdown, and calls the *same* `ingest_document` choke point the corpus directory uses. Nothing is
  written to `knowledge/`; an uploaded document is a database document, and the corpus stays the
  reviewed set.

- **Expensive results are cached by identity.** `kb_extractions` is keyed by
  `(content_hash, profile_hash)`, where `profile_hash` is a fingerprint of the reader configuration.
  The same bytes with the same profile are never read twice; a profile change re-reads the file
  instead of silently reusing a result produced by other thresholds. A refusal is cached too: a
  blurred scan does not cost seconds on every retry.

- **A refusal completes the job.** Below the quality gate, one page over the confidence floor, or
  coverage under the acceptance policy refuses the whole document — a half-indexed regulation
  answers wrongly with confidence. The reason is recorded and shown in the cabinet; the bytes stay
  available for a better profile.

## Consequences

- The 100% of the current corpus that is born-digital costs nothing: the `native` profile has
  `family: none`, needs no recognizer, and a scanned page is refused with `unsupported`, never
  guessed at. Recognition is an opt-in extra (`uv sync --extra ocr`).
- Every refusal is actionable: a recruiter sees `low_confidence` or `blurry` and re-shoots the page,
  instead of filing a bug against "the bot". Glare has no pre-recognition score — white paper reads
  as 100% glare — so overexposure is caught where it is measurable: by the recognizer's confidence.
- The quality gate runs on the artifact the engine will consume, so its thresholds are calibrated
  per profile, not per deployment.
- Two dependency layers exist on purpose: `pypdfium2` and `python-pptx` are core (reading a PDF is
  not optional), while `rapidocr` and `onnxruntime` are an extra. `make check` and the whole test
  suite pass without the extra installed.
- A new engine is one class in `ocr.py` plus one value in the profile schema; the routers, the job,
  the API, and the tests do not change.
- No new infrastructure: `kb_files`, `kb_extractions`, and the `jobs` row live in the one Postgres
  ([0005](0005-single-postgres.md)).
- Extraction quality is not claimed, it is measured: `docs/evals/ocr.yaml` and `make eval-ocr` score
  character error rate and refusal correctness on a fixed set, and a regression fails the build.
  A clean render is a floor, not a photograph — see `docs/measurements/` for what was actually run.
- Deleting a file remains `DATA_RETENTION_DAYS` work: uploads are purged with the rest of the data,
  and the extraction cache holds no bytes, only the markdown that became a document.
