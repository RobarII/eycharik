# Measurement 2026-10-25 — token budget of one answer, per tokenizer

- Date: 2026-10-25
- Commit: `8ea934f`
- Environment: local macOS, `uv run --with tokenizers`, tokenizer files from the model repositories
- Commands:

```bash
HUB=~/.cache/huggingface/hub
hf download ai-sage/GigaChat3.1-10B-A1.8B tokenizer.json
hf download Qwen/Qwen3.5-9B tokenizer.json
hf download t-tech/T-lite-it-2.1 tokenizer.json
hf download deepseek-ai/DeepSeek-V4-Flash tokenizer.json
hf download zai-org/GLM-5.3-flash tokenizer.json
hf download openai/gpt-oss-120b tokenizer.json
hf download BAAI/bge-reranker-v2-m3 tokenizer.json
hf download BAAI/bge-m3 tokenizer.json

uv run --with tokenizers python scripts/token_budget.py \
  --tokenizer $HUB/models--ai-sage--GigaChat3.1-10B-A1.8B/snapshots/*/tokenizer.json \
  --tokenizer $HUB/models--Qwen--Qwen3.5-9B/snapshots/*/tokenizer.json \
  --tokenizer $HUB/models--t-tech--T-lite-it-2.1/snapshots/*/tokenizer.json \
  --tokenizer $HUB/models--deepseek-ai--DeepSeek-V4-Flash/snapshots/*/tokenizer.json \
  --tokenizer $HUB/models--zai-org--GLM-5.3-flash/snapshots/*/tokenizer.json \
  --tokenizer $HUB/models--openai--gpt-oss-120b/snapshots/*/tokenizer.json \
  --rerank-tokenizer $HUB/models--BAAI--bge-reranker-v2-m3/snapshots/*/tokenizer.json \
  --prompt docs/prompts/answer/v7.md --chunks 5 --completion-chars 700
```

- Output:

```text
prompt docs/prompts/answer/v7.md, 89 chunks from 71 files
answer sample 700 chars, context 5 chunks
rerank 30 candidates -> 6272 tokens (.../bge-reranker-v2-m3/snapshots/953dc6f6.../tokenizer.json)
tokenizer                                            prompt  chunk     in   out  total
--------------------------------------------------------------------------------------
ai-sage--GigaChat3.1-10B-A1.8B                         1078    226   2208   175   2383
Qwen--Qwen3.5-9B                                       1211    261   2516   178   2694
t-tech--T-lite-it-2.1                                  1078    231   2233   171   2404
deepseek-ai--DeepSeek-V4-Flash                         1316    282   2726   177   2903
zai-org--GLM-5.3-flash                                 1211    256   2491   170   2661
openai--gpt-oss-120b                                   1196    251   2451   169   2620
```

Embedding token count for the corpus, with `BAAI/bge-m3`'s tokenizer: **20 785 tokens** over the
same 89 chunks; a sample question («Как получить доступ к корпоративному порталу?») is 11 tokens.

## What this measures

- The answer prompt ([v7](../prompts/answer/v7.md)) and five retrieved chunks, chunked by the
  production chunker (`DEFAULT_MAX_CHARS = 1200`) over the current `knowledge/` corpus.
- The completion, as a **fixed-length Russian fragment of 700 characters** measured with each
  tokenizer. This makes models comparable without pretending we know the future answers.
- What the reranker sees: 30 candidate chunks plus the question, with the reranker's own tokenizer.

## What this does not measure

- **The actual answers.** 700 characters is a budget chosen from the answer policy's tone
  ("two to four sentences plus a link"), not an average of real completions. The profile ceiling is
  700 tokens, which is four times the measured 175, so the worst case is bounded, not observed.
- **The retrieval fan-out on a real query.** The 30 candidates are the first 30 corpus chunks, not
  the fused list of a live question. The token count per chunk is what matters and it is stable.
- **Throughput or latency.** Token counts say nothing about time to first token.
- **Quality.** Only [golden.yaml](../evals/golden.yaml) says whether an answer is right.

## Why this replaced a single-tokenizer number

The previous revision of this measurement used only the GigaChat tokenizer and priced five models
with it. The spread between tokenizers on the same Russian prompt is **1 078 → 1 316 tokens (+22%)**
and on the same corpus chunk **226 → 282 (+25%)**. Applying one number to another vendor's price
understates Qwen by 14% and DeepSeek by 23%. That is the size of a discount negotiation, so the
measurement now carries one row per tokenizer.

## Derived numbers

Per answer: `(input × price_in + completion × price_out) / 1e6`, per model, with the prices and the
class of each price in [vendor-comparison.md](../product/vendor-comparison.md).

| Model | Input | Completion | ₽/answer including rerank |
|---|---|---|---|
| `GigaChat3-10B-A1.8B` | 2 208 | 175 | 0.0306 |
| `gpt-oss-120b` | 2 451 | 169 | 0.0507 |
| `DeepSeek V4 Flash` | 2 726 | 177 | 0.1349 |
| `Qwen-3.8-Flash-Next` | 2 516 | 178 | 0.0649 |
| `GLM-5.3-flash` | 2 491 | 170 | 0.2297 |

A full eval run (137 cases) is ≈ 4 ₽ on the cheapest model: the evals are not the expense, the
traffic is.
