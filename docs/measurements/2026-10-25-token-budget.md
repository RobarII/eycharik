---
title: 'Оценка 2026-10-25: бюджет токенов'
summary: 'Сколько токенов стоит один ответ по промпту v7 у шести моделей: у каждой свой токенизатор. Отсюда цена ответа и прогона оценки.'
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-25 — пройдена

- дата: `2026-10-25`
- окружение: `local` macOS, `uv run --with tokenizers`, файлы токенизаторов из репозиториев моделей
- коммит: `8ea934f`
- команда: `uv run --with tokenizers python scripts/token_budget.py --tokenizer $HUB/models--ai-sage--GigaChat3.1-10B-A1.8B/snapshots/*/tokenizer.json --tokenizer $HUB/models--Qwen--Qwen3.5-9B/snapshots/*/tokenizer.json --tokenizer $HUB/models--t-tech--T-lite-it-2.1/snapshots/*/tokenizer.json --tokenizer $HUB/models--deepseek-ai--DeepSeek-V4-Flash/snapshots/*/tokenizer.json --tokenizer $HUB/models--zai-org--GLM-5.3-flash/snapshots/*/tokenizer.json --tokenizer $HUB/models--openai--gpt-oss-120b/snapshots/*/tokenizer.json --rerank-tokenizer $HUB/models--BAAI--bge-reranker-v2-m3/snapshots/*/tokenizer.json --prompt docs/prompts/answer/v7.md --chunks 5 --completion-chars 700`
- токенизаторы: шесть моделей плюс переранжировщик; скачивание файлов — в блоке ниже

Скачивание:

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
```

Что показал прогон:

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

Токенов эмбеддинга по корпусу с токенизатором `BAAI/bge-m3`: 20 785 токенов на тех же
89 фрагментах. Пример вопроса («Как получить доступ к корпоративному порталу?») — 11 токенов.

## Что измеряется

- Промпт ответа ([v7](../prompts/answer/v7.md)) и пять найденных фрагментов, нарезанных
  производственной нарезкой (`DEFAULT_MAX_CHARS = 1200`) по текущему корпусу `knowledge/`.
- Ответ — фиксированный русский фрагмент длиной 700 символов, посчитанный каждым токенизатором.
  Так модели сравнимы без догадок о будущих ответах.
- Что видит переранжировщик: 30 фрагментов-кандидатов плюс вопрос, его собственным токенизатором.

## Что не измеряется

- Настоящие ответы. 700 символов — бюджет из тона политики ответов («два-четыре предложения
  плюс ссылка»), не среднее по реальным ответам. Потолок профиля — 700 токенов, вчетверо больше
  измеренных 175, то есть худший случай ограничен, но не измерен.
- Веер поиска на живом запросе. 30 кандидатов — первые 30 фрагментов корпуса, не слитый список
  живого вопроса. Здесь важен счёт токенов на фрагмент, и он устойчив.
- Пропускная способность и задержка. Счёт токенов ничего не говорит о времени до первого токена.
- Качество. Право на ответ даёт только [golden.yaml](../evals/golden.yaml).

## Почему это заменило число по одному токенизатору

Прошлая редакция измерения брала только токенизатор GigaChat и оценивала им пять моделей. Разброс
между токенизаторами на одном русском промпте — от 1 078 до 1 316 токенов (+22%), на одном
фрагменте корпуса — от 226 до 282 (+25%). Одно число, приложенное к цене другого вендора, занижает Qwen на 14%,
а DeepSeek на 23%. Это размер скидки на переговорах, поэтому теперь в измерении своя строка
на каждый токенизатор.

## Производные числа

На ответ: `(input × price_in + completion × price_out) / 1e6` для каждой модели; цены и класс
каждой цены — в [vendor-comparison.md](../product/vendor-comparison.md).

| модель | вход | выход | ₽/ответ с переранжированием |
|---|---|---|---|
| `GigaChat3-10B-A1.8B` | 2 208 | 175 | 0.0306 |
| `gpt-oss-120b` | 2 451 | 169 | 0.0507 |
| `DeepSeek V4 Flash` | 2 726 | 177 | 0.1349 |
| `Qwen-3.8-Flash-Next` | 2 516 | 178 | 0.0649 |
| `GLM-5.3-flash` | 2 491 | 170 | 0.2297 |

Полный прогон оценки (137 кейсов) ≈ 4 ₽ на самой дешёвой модели: расход не в оценках, а в трафике.

Кейсы по одному — в артефакте `2026-10-25-token-budget.jsonl` рядом с этим файлом.
