"""Measure the prompt, context, completion, and rerank token budget per tokenizer.

Unit economics need "how many tokens does one answer cost". It has three parts: the answer prompt,
the chunks the retriever puts in front, and the completion. Every vendor bills its own tokenizer, so
one measurement reused across five models quietly lies by 10-25%. This script takes several
tokenizer files and prints one row per tokenizer.

The completion is a budget, not a measurement: a real Russian fragment of the corpus is truncated to
`--completion-chars` and tokenized with each tokenizer, so the comparison is like-for-like without
pretending to know the answers. `--rerank-tokenizer` adds what a cross-encoder sees per answer.

    HUB=~/.cache/huggingface/hub
    hf download ai-sage/GigaChat3.1-10B-A1.8B tokenizer.json
    hf download Qwen/Qwen3.5-9B tokenizer.json
    uv run --with tokenizers python scripts/token_budget.py \
        --tokenizer $HUB/models--ai-sage--GigaChat3.1-10B-A1.8B/snapshots/*/tokenizer.json \
        --tokenizer $HUB/models--Qwen--Qwen3.5-9B/snapshots/*/tokenizer.json \
        --rerank-tokenizer $HUB/models--BAAI--bge-reranker-v2-m3/snapshots/*/tokenizer.json \
        --prompt docs/prompts/answer/v7.md --chunks 5 --completion-chars 700
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
from onboarding.core.models import Chunk, DocId, Document  # noqa: E402


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


def _chunks(root: Path) -> list[Chunk]:
    return [
        chunk
        for document in _documents(root)
        for chunk in split_document(document, max_chars=DEFAULT_MAX_CHARS)
    ]


def _answer_sample(chunks: list[Chunk], chars: int) -> str:
    """A deterministic Russian fragment of the corpus, used as the answer-length probe."""
    text = " ".join(chunk.text for chunk in chunks)
    return text[:chars]


def _percentile(values: list[int], share: float) -> int:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))]


def _row(
    name: str,
    tokenizer: Tokenizer,
    *,
    prompt: str,
    chunks: list[Chunk],
    sample: str,
    context_chunks: int,
) -> dict[str, object]:
    prompt_tokens = len(tokenizer.encode(prompt).ids)
    chunk_tokens = [len(tokenizer.encode(chunk.text).ids) for chunk in chunks]
    mean_chunk = round(statistics.mean(chunk_tokens))
    completion_tokens = len(tokenizer.encode(sample).ids)
    input_tokens = prompt_tokens + context_chunks * mean_chunk
    return {
        "tokenizer": name,
        "prompt_tokens": prompt_tokens,
        "chunk_tokens_mean": mean_chunk,
        "chunk_tokens_p95": _percentile(chunk_tokens, 0.95),
        "context_tokens": context_chunks * mean_chunk,
        "input_tokens": input_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": input_tokens + completion_tokens,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer", required=True, action="append", type=Path)
    parser.add_argument("--prompt", type=Path, default=ROOT / "docs/prompts/answer/v7.md")
    parser.add_argument("--knowledge", type=Path, default=ROOT / "knowledge")
    parser.add_argument("--chunks", type=int, default=5)
    parser.add_argument("--completion-chars", type=int, default=700)
    parser.add_argument("--rerank-tokenizer", type=Path)
    parser.add_argument("--rerank-candidates", type=int, default=30)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    prompt = args.prompt.read_text(encoding="utf-8")
    chunks = _chunks(args.knowledge)
    sample = _answer_sample(chunks, args.completion_chars)

    rerank_tokens = 0
    if args.rerank_tokenizer is not None:
        rerank_tokenizer = Tokenizer.from_file(str(args.rerank_tokenizer))
        candidates = [chunk.text for chunk in chunks[: args.rerank_candidates]]
        rerank_tokens = len(rerank_tokenizer.encode(" ".join(candidates)).ids)

    rows = []
    for path in args.tokenizer:
        name = next(
            (part.split("models--")[1] for part in path.parts if "models--" in part),
            path.name,
        )
        rows.append(
            _row(
                name,
                Tokenizer.from_file(str(path)),
                prompt=prompt,
                chunks=chunks,
                sample=sample,
                context_chunks=args.chunks,
            )
        )

    report = {
        "prompt": str(args.prompt.relative_to(ROOT)),
        "knowledge_files": len({chunk.id.split("#")[0] for chunk in chunks}),
        "chunks": len(chunks),
        "context_chunks": args.chunks,
        "completion_chars": args.completion_chars,
        "rerank_candidates": args.rerank_candidates,
        "rerank_tokens": rerank_tokens,
        "rows": rows,
    }
    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(
        f"prompt {report['prompt']}, {report['chunks']} chunks "
        f"from {report['knowledge_files']} files"
    )
    print(f"answer sample {args.completion_chars} chars, context {args.chunks} chunks")
    if rerank_tokens:
        print(f"rerank {args.rerank_candidates} candidates -> {rerank_tokens} tokens "
              f"({args.rerank_tokenizer})")
    header = f"{'tokenizer':<52}{'prompt':>7}{'chunk':>7}{'in':>7}{'out':>6}{'total':>7}"
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{str(row['tokenizer'])[:50]:<52}{row['prompt_tokens']:>7}{row['chunk_tokens_mean']:>7}"
            f"{row['input_tokens']:>7}{row['completion_tokens']:>6}{row['total_tokens']:>7}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
