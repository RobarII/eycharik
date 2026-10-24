---
title: Миграция базы
summary: Правила правки схемы, проверка на черновой базе и вывод базы из чужой линии ревизий.
kind: прогон
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Прогон: миграция базы

## Правила

- Миграции только вперёд. Ошибку исправляет следующая миграция.
- Базовая `0001_initial` создаёт схему из метаданных SQLAlchemy. Дальнейшие миграции пишутся руками
  и проходят ревью.
- Миграция, которая переписывает большую таблицу, делится: добавить, забэкфиллить, переключить
  чтение.
- `EMBED_DIM` зашит в колонку `kb_chunks.embedding` и её HNSW-индекс. Смена модели эмбеддингов — миграция, а не настройка.

## Шаги

1. Напишите ревизию в `apps/api/onboarding/migrations/versions/`.
2. Примените её к черновой базе:

```bash
DATABASE_URL=postgresql+asyncpg://onboarding:onboarding@localhost:5432/onboarding \
  uv run alembic upgrade head
```

3. Прогоните интеграционный набор по этой базе:

```bash
ONBOARDING_TEST_DATABASE=<same url> uv run pytest -m integration
```

4. Запускайте бэкфилл отдельной командой, никогда внутри миграции, когда таблица большая.
5. Выкатывайте воркер до `api`, если миграция меняет колонку, которую читает вебхук.

## Проверка

```bash
uv run alembic current
uv run alembic upgrade head --sql | head    # review the SQL before applying
```

`alembic check` не используется: базовая ревизия отражает метаданные на своём момент, а поздние
миграции законно от него уходят, пока autogenerate не переразмечен.

## База из feature-ветки

Две ветки, каждая добавила по миграции, дают две истории, и одно и то же изменение может получить
разные номера. Базу, помеченную одной из них, другая не поднимет:

```
ERROR [alembic.util.messaging] Can't locate revision identified by '0011_channel_address'
```

Здесь ветка добавила `channel_address` как `0011`; в `main` та же миграция — `0014`, а ревизии с `0011` по `0013`
ушли на колонку изображения, таблицу состояния индекса и владельца вопроса. Не удаляйте строки из
`alembic_version` и не правьте схему руками. Переставьте метку на последнюю ревизию, с которой
согласны обе истории, и дайте alembic применить остальное:

```bash
# 1. What does the database claim, and what does this tree know? (the error above names the gap)
docker exec $PG psql -U onboarding -d $DB -tAc 'select version_num from alembic_version'
uv run alembic history | head

# 2. Before moving the stamp, diff the two migrations if the ids diverge:
#    if the bodies are identical, the later one is a no-op because it inspects the catalog first
diff <(sed -n '/^def upgrade/,$p' old_revision.py) <(sed -n '/^def upgrade/,$p' new_revision.py)

# 3. Re-anchor to the last common revision and upgrade. A migration that guards every step with
#    an inspector is safe to run on a schema that already has its columns.
docker exec $PG psql -U onboarding -d $DB -c \
  "update alembic_version set version_num='0010_messages_retention'"
uv run alembic upgrade head
docker exec $PG psql -U onboarding -d $DB -tAc 'select version_num from alembic_version'
```

Затем докажите, что схема, нужная коду, существует, а не только метка:

```sql
select column_name from information_schema.columns
  where table_name = 'messages' and column_name in ('image', 'channel');
```

Воркер, запущенный до этого момента, падает на первой исходящей аренде с
`column messages.image does not exist` и держит строку в ожидании, поэтому симптом — тишина, а не
цикл падений.

## Откат

В продакшене не поддерживается. Если миграция неверна, выпустите исправляющую миграцию и запишите
инцидент.
