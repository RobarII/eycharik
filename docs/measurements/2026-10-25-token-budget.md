# Measurement 2026-10-25 — token budget of one answer

- Date: 2026-10-25
- Commit: `dcc2175`
- Environment: local macOS, `uv run --with tokenizers`, Python 3.x, tokenizer downloaded from
  `ai-sage/GigaChat3.1-10B-A1.8B`
- Command:

```bash
hf download ai-sage/GigaChat3.1-10B-A1.8B tokenizer.json
uv run --with tokenizers python scripts/token_budget.py \
  --tokenizer "$HOME/.cache/huggingface/hub/models--ai-sage--GigaChat3.1-10B-A1.8B/snapshots"/*/tokenizer.json \
  --prompt docs/prompts/answer/v7.md --chunks 5 --completion 250
```

- Output:

```text
tokenizer           .../models--ai-sage--GigaChat3.1-10B-A1.8B/snapshots/99ef74e6.../tokenizer.json
prompt              docs/prompts/answer/v7.md (1078 tokens)
chunks              89 from 71 files
chunk tokens        mean 226 median 244 p95 299 max 319
context             5 chunks -> 1130 tokens
input per answer    2208 tokens
completion budget   250 tokens
total per answer    2458 tokens
```

## What this measures

The input side of one answer, offline, with the production chunker over the current `knowledge/`
corpus: the system prompt, plus five retrieved chunks at `DEFAULT_MAX_CHARS = 1200`. The chunk
distribution is tight because every chunk is capped; the mean is the number to use, the p95 is the
pessimistic one.

## What this does not measure

- **The completion.** 250 tokens per answer is a budget, not a measurement: the profile caps output
  at 700 tokens. The unit economics carry both (`250` typical, `700` worst case).
- **The retrieval fan-out.** Five chunks is `RERANK_LIMIT`-style context, not the number of
  candidates the reranker sees. The vendor comparison prices the reranker at 30 candidates, which
  matches the fused list in [0003](../decisions/0003-hybrid-retrieval.md).
- **Quality.** Token counts say nothing about whether the answer is right;
  [golden.yaml](../evals/golden.yaml) does.

## Derived numbers

Every per-answer price in [vendor-comparison.md](../product/vendor-comparison.md) is
`(input_tokens × input_price + completion_tokens × output_price) / 1e6`, with these token counts and
prices read from vendor price lists on 2026-10-25. The corpus reindex is one-off: 89 chunks × 226
tokens ≈ 20 114 tokens, i.e. 0.012 ₽ with the cheapest embedder and 0.65 ₽ with the most expensive
one on the list. A full eval run (137 cases, 2458 tokens each) costs ≈ 4 ₽ on the cheapest model —
the evals are not the expense, the traffic is.
