#!/usr/bin/env python3
"""Measure the prompt and context token budget of the answer path.

The number that matters for unit economics is "how many tokens does one answer cost". It has
three parts: the answer prompt, the chunks the retriever puts in front of it, and the completion.
The first two are measurable offline without a provider: chunk the corpus with the production
chunker, then tokenize prompt + N chunks with the tokenizer of the model under consideration. The
completion is a policy value, not a measurement, and it is passed in with `--completion`.

The tokenizer file comes from the model repository (`hf download <repo> tokenizer.json`), so the
result is tied to a named model rather than to a tokenizer guess:

    hf download ai-sage/GigaChat3.1-10B-A1.8B tokenizer.json
    uv run --with tokenizers python scripts/token_budget.py \
        --tokenizer "$HOME/.cache/huggingface/hub/models--ai-sage--GigaChat3.1-10B-A1.8B/"\
"snapshots"/*/tokenizer.json \
        --prompt docs/prompts/answer/v7.md --chunks 5 --completion 250
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import date
from pathlib import Path

from tokenizers import Tokenizer  # type: ignore[import-not-found]

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from onboarding.core.chunking import DEFAULT_MAX_CHARS, split_document  # noqa: E402
from onboarding.core.models import DocId, Document  # noqa: E402


def _documents(root: Path) -> list[Document]:
    documents: list[Document] = []
    for path in sorted(root.rglob("*.md")):
        documents.append(
            Document(
                id=DocId(str(path.relative_to(ROOT))),
                title=path.stem,
                text=path.read_text(encoding="utf-8"),
                audience=("all",),
                valid_from=date(2026, 1, 1),
            )
        )
    return documents


def _percentile(values: list[int], share: float) -> int:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer", required=True, type=Path)
    parser.add_argument("--prompt", type=Path, default=ROOT / "docs/prompts/answer/v7.md")
    parser.add_argument("--knowledge", type=Path, default=ROOT / "knowledge")
    parser.add_argument("--chunks", type=int, default=5)
    parser.add_argument("--completion", type=int, default=250)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    tokenizer = Tokenizer.from_file(str(args.tokenizer))
    prompt_tokens = len(tokenizer.encode(args.prompt.read_text(encoding="utf-8")).ids)

    chunks = [
        chunk
        for document in _documents(args.knowledge)
        for chunk in split_document(document, max_chars=DEFAULT_MAX_CHARS)
    ]
    chunk_tokens = [len(tokenizer.encode(chunk.text).ids) for chunk in chunks]
    mean_chunk = round(statistics.mean(chunk_tokens))

    input_tokens = prompt_tokens + args.chunks * mean_chunk
    report = {
        "tokenizer": str(args.tokenizer),
        "prompt": str(args.prompt.relative_to(ROOT)),
        "prompt_tokens": prompt_tokens,
        "knowledge_files": len({chunk.id.split("#")[0] for chunk in chunks}),
        "chunks": len(chunks),
        "chunk_tokens_mean": mean_chunk,
        "chunk_tokens_median": round(statistics.median(chunk_tokens)),
        "chunk_tokens_p95": _percentile(chunk_tokens, 0.95),
        "chunk_tokens_max": max(chunk_tokens),
        "context_chunks": args.chunks,
        "input_tokens": input_tokens,
        "completion_tokens": args.completion,
        "total_tokens": input_tokens + args.completion,
    }
    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"tokenizer           {report['tokenizer']}")
    print(f"prompt              {report['prompt']} ({prompt_tokens} tokens)")
    print(f"chunks              {len(chunks)} from {report['knowledge_files']} files")
    print(
        "chunk tokens        mean {chunk_tokens_mean} median {chunk_tokens_median} "
        "p95 {chunk_tokens_p95} max {chunk_tokens_max}".format(**report)
    )
    print(f"context             {args.chunks} chunks -> {args.chunks * mean_chunk} tokens")
    print(f"input per answer    {input_tokens} tokens")
    print(f"completion budget   {args.completion} tokens")
    print(f"total per answer    {input_tokens + args.completion} tokens")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
