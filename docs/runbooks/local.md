---
title: Локальный стек
summary: Как поднять compose, чем пустая база отличается от демо, как наполнить и обнулить её и какие команды есть в Makefile.
kind: прогон
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-25
---

# Локальный стек

`docker compose up -d --build` поднимает PostgreSQL, миграции, api, воркер и статический
кабинет. Сидов нет намеренно: база пустая, поэтому после входа кабинет показывает нулевые
счётчики и пустые списки.

Откройте <http://localhost:3000> и войдите с `dev-hr-token` (или `dev-recruiter-token` для
скоупа рекрутёра).

Умолчания compose — локальный офлайн-профиль (ответы от `extractive`-провайдера, хеширующие
эмбеддинги) и демо-токены администратора. Для потока «пусто/демо» файл `.env` не нужен. Чтобы
включить настоящие модели и MAX, скопируйте `.env.example` в `.env` и задайте ключи.

## Наполнить демо-данными

Из корня репозитория:

```bash
make demo-data
```

Если `make` не установлен (частое дело на Windows), возьмите обёртку:

```powershell
.\demo-data.cmd
```

Обе команды запускают `ingest` и демо-сид внутри образа api, поэтому нужен Docker Compose, а
локальное окружение Python не нужно. Сид создаёт трёх сотрудников, их прогоны и риски, три
вопроса и индексирует `knowledge/`.

## Убрать демо-данные

```bash
make demo-data-del
```

На Windows без `make`:

```powershell
.\demo-data-del.cmd
```

Обе команды чистят runtime-таблицы, удаляют демо-сотрудников с `1001` по `1003` и очищают
проиндексированную базу знаний (SQL лежит в `scripts/demo-data-del.sql`). Кабинет возвращается
в пустое состояние. Это локальный сброс для демо: он уносит и документы базы знаний, и
runtime-строки, поэтому не запускайте его на том, что вам дорого.

## Полный сброс

```bash
docker compose down -v
docker compose up -d --build
```

`-v` удаляет том PostgreSQL; следующий старт снова пустой. Миграции идут автоматически.

Если `make` не установлен, команда наполнения такая:

```bash
docker compose run --rm api python -m onboarding.cli ingest
docker compose run --rm api python -m onboarding.cli demo --reset --yes
```

## Быстрые команды

```bash
make install       # create the virtual environment
make check         # ruff, mypy, import contracts, unit tests, docs links, admin
make verify        # the gate: check plus integration tier, coverage floor and the cabinet
make verify-demo   # end-to-end: stack, seed, and the numbers through the admin API
make security      # pip-audit, npm audit, actionlint, shellcheck, hadolint, gitleaks
make admin-e2e-stack  # the cabinet against the running stack, not the fixture
make doctor        # read-only preflight: tools, ports, state
make demo          # compose up, seed, print the door and the token
make demo-live     # the same with real models from .env.live (free tier works)
make nuke          # destructive: drops the compose volume and the local demo database
make test-cov      # offline + postgres with the coverage floor (a part of make verify)
make eval          # golden-set retrieval, generation, escalation
make ingest        # index knowledge/ into pgvector
make demo-data     # docker compose: ingest + three employees, risks, three questions
make demo-data-del # docker compose: return the cabinet to empty
make run           # api with reload on :8000
make worker        # job loop, outbox dispatcher, reminder tick
make cron          # one scheduler pass for reminders and the outbox (crontab-friendly)
make admin-install # cabinet dependencies
make admin-dev     # recruiter cabinet on :5173
make up            # postgres + migrate + api + worker + cabinet, no demo seed
make prod-config   # validate docker-compose.prod.yml with .env.prod
make smoke         # public health, webhook, cabinet headers, metrics exposure
make backup        # verified Postgres dump; BACKUP_S3_URI enables offsite upload
```

Дальше: [проверка за десять минут](../checker.md) — что запустить и какой вывод считать успехом,
[деплой](deploy.md) — как выкатить то же самое на VM.
