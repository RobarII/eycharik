---
title: Деплой
summary: Как выкатить прод на одну VM, проверить его смоуком и откатиться на прошлый образ.
kind: прогон
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-25
---

# Прогон: деплой

Деплой — одна VM с compose-стеком за nginx хоста. Образы собираются в CI, публикуются в GHCR и
тянутся по неизменяемому SHA коммита. Хост никогда не собирает образ, и nginx — единственный
процесс, слушающий 443.

Прод получает только выпущенный коммит: `main` собирает образ, человек ставит релизный тег, деплой
идёт следом. Merge в `main` сам по себе прод не трогает — см.
[ADR 0028](../decisions/0028-one-image-per-commit.md).

Текущий демо-хост: `bot.state3407.space` на VPS 1 vCPU / 921 MB
([запас по мощности](../measurements/2026-10-23-demo-vps-capacity.md)). Этого хватает для демо, не
для реальных данных сотрудников: VPS вне России (152-ФЗ), и запас RAM тонкий. Пилот переезжает на
российский хост с 2–4 GB и теми же compose-файлами.

## Условия

- `make check` зелёный. `make eval-retrieval` зелёный; `make eval` зелёный, если провайдер доступен.
- У изменения схемы есть миграция в `apps/api/onboarding/migrations/versions/`.
- На коммите есть успешный чек `gate` — тот самый job из `.github/workflows/ci.yml`. Ручной деплой
  проверяет его через API и без него отказывается идти.
- Релизный workflow выпустил `ghcr.io/<owner>/moshackathon-api` и `-admin` под `sha-<sha>`, а тег
  `vX.Y.Z` указывает на тот же диджест. Деплой тоже проверяет, что оба образа тянутся.
- `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PORT`, `DEPLOY_PATH` — переменные репозитория;
  `DEPLOY_SSH_KEY` и `DEPLOY_KNOWN_HOSTS` — секреты репозитория или окружения `production`.
- Окружение `production` существует. Если тариф поддерживает правила защиты, добавьте обязательного
  ревьюера; иначе человеческий барьер — пуш релизного тега, а теги ставит человек, не бот.
- `DEPLOY_NOTIFY_URL` (необязательно) — вебхук, куда деплой пишет `failed` или `deployed`. Без него
  сломанный выкат видит только тот, кто смотрел в лог workflow.

## Первичная настройка хоста

Сначала сгенерируйте отдельный ключ CI; приватная половина идёт в секрет `DEPLOY_SSH_KEY`,
публичная — в команду настройки:

```bash
ssh-keygen -t ed25519 -C github-actions-onboarding -f /tmp/onboarding_deploy -N ''
```

Запустите от root из чекаута этого репозитория:

```bash
DOMAIN=bot.example.com \
ACME_EMAIL=ops@example.com \
DEPLOY_PUBKEY="$(cat /tmp/onboarding_deploy.pub)" \
REPO_URL=git@github.com:owner/repo.git \
scripts/bootstrap-vps.sh
```

Скрипт ставит недостающие пакеты, создаёт непривилегированного пользователя `deploy`, создаёт
`/opt/onboarding` и `/var/backups/onboarding`, ставит ACME-vhost, выпускает сертификат, ставит
TLS-vhost и включает таймер бэкапа. Он не трогает другие сайты nginx, конфигурацию SSH и файрвол.

Затем под `deploy`:

```bash
cd /opt/onboarding
docker login ghcr.io -u <github-user>          # read:packages token, stored on the host
cp .env.production.example .env.prod && chmod 600 .env.prod
$EDITOR .env.prod
```

`ENVIRONMENT=production` отказывается стартовать без `MAX_BOT_TOKEN`, `MAX_WEBHOOK_SECRET`,
`LLM_API_KEY`, `ADMIN_TOKENS`, `METRICS_TOKEN` и `INBOUND_FILES_KEY`. Ключ — base64 от 32 байт:

```bash
python3 -c 'import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())'
```

Он шифрует документы, которые люди присылают в чат. Потеря ключа не ломает бота: новые файлы
получат статус `unavailable`, а старые перестанут скачиваться. Храните его там же, где остальные
секреты, и не меняйте без ротации: старые блобы читаются только своим ключом. Демо-выбор модели требует ещё `EMBED_API_KEY` для
OpenRouter; GigaChat использует один ключ на обе роли. Образ `api` уже ставит Russian Trusted CA и
указывает `MAX_CA_BUNDLE` на объединённый системный бандл.

Пример окружения выбирает OpenCode Go для ответов и OpenRouter Qwen3 для эмбеддингов. Оба эндпоинта
отвечают с демо-хоста, и ни одна модель на нём не работает. Блок GigaChat закомментирован для
пилота на российском хосте по 152-ФЗ; см.
[ADR 0025](../decisions/0025-demo-models-on-opencode-and-openrouter.md).

Один раз добавьте ключ хоста в секрет CI:

```bash
ssh-keyscan -p 22 "$DEPLOY_HOST" 2>/dev/null
```

Положите вывод в `DEPLOY_KNOWN_HOSTS`. Не используйте `StrictHostKeyChecking=no` в CI.

## Релиз

Сначала коммит попадает в `main`: workflow `release` собирает оба образа и публикует их под
`sha-<sha>` с provenance и SBOM. Дальше версию присваивает человек:

```bash
git tag v1.2.3
git push origin v1.2.3
```

Пуш тега запускает джобу `promote`: она копирует опубликованный диджест под `v1.2.3`, ничего не
пересобирая. Если образа для этого SHA нет, джоба падает и говорит, что коммит надо сначала
влить в `main`. Деплой-workflow идёт после успешного релиза, ждёт одобрения окружения `production`,
если тариф это поддерживает, и вызывает `scripts/deploy-remote.sh <sha>` по SSH.

Удалённый скрипт по порядку:

1. Берёт блокировку деплоя и запоминает прошлый SHA.
2. Забирает коммит и переключается на него.
3. Тянет образы `api`, воркера, миграций и кабинета.
4. Запускает Postgres и ждёт его health check.
5. Снимает дамп базы в `/var/backups/onboarding/pre-deploy-<время>-<sha>.dump` и проверяет, что
   `pg_restore` его читает.
6. Прогоняет `alembic upgrade head` один раз, до старта любых новых процессов. Падение миграции
   останавливает деплой: скрипт не откатывает образы на сдвинутую схему, а называет дамп.
7. Запускает воркер, затем `api` и кабинет.
8. Ждёт health `api` и кабинета, трижды с паузой прогоняет `scripts/smoke.sh`, записывает
   `.deployed_sha` и уведомляет `DEPLOY_NOTIFY_URL`.
9. При сбое до шага 6 выкатывает прошлый SHA и снова гоняет смоук.

Ручной деплой или откат на уже выпущенный SHA:

```bash
gh workflow run deploy.yml -f sha=<40-character-sha>
```

## Смоук-тест

`scripts/smoke.sh` проверяет:

- `/healthz` возвращает `{"status":"ok"}`.
- `/readyz` — `200` (база отвечает).
- `POST /webhook/max` без секрета — `401`.
- Ответ кабинета несёт CSP, `X-Frame-Options: DENY` и `nosniff`.
- `/metrics` не публичен (`401` или `403`).

Запускать откуда угодно:

```bash
BASE_URL=https://bot.example.com scripts/smoke.sh
```

## Регистрация подписки

Когда хост и секрет на месте:

Запускайте это на хосте под `deploy`; контейнер несёт российский CA и продовое окружение:

```bash
HOST=bot.example.com
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod \
  run --rm --no-deps api python -m onboarding.cli subscribe \
  --url "https://$HOST/webhook/max" \
  --types message_created,bot_started
```

Повторный запуск заменяет подписку для этого бота. Туннели меняют имена хостов; перерегистрируйте
после каждого перезапуска туннеля. Telegram и VK регистрируют вебхуки своим способом; этот же
ранбук покрывает оба.

Отправьте `/start` с тестового аккаунта. Ожидается: строка `events`, строка `jobs`, которая доходит
до `done`, строка `outbox`, которая доходит до `sent`, и одно приветственное сообщение в MAX.

## Проверочные запросы

```sql
select status, count(*) from jobs group by status;
select status, count(*) from messages group by status;
select name, count(*) from audit_log group by name order by 2 desc;
select count(*) filter (where resolved_at is not null) as resolved, count(*) from questions;
```

Строки `messages` в `pending` значат, что падает диспетчер или MAX API; читайте `last_error`.

Проверьте заголовки кабинета по HTTPS:

```bash
curl -sI https://$HOST/ | grep -iE 'content-security-policy|x-frame|x-content-type|referrer'
```

`apps/admin/nginx.conf` отдаёт политику без `unsafe-inline` для скриптов, с `frame-ancestors 'none'`,
`nosniff` и `no-referrer`. Если чего-то нет, прокси перед контейнером срезает заголовки: почините
это до передачи кабинета рекрутёрам. Кука сессии `Secure`, поэтому хост по простому HTTP молча
теряет вход.

## Откат

Выкатите прошлый тег образа:

```bash
gh workflow run deploy.yml -f sha=<previous-sha>
```

Не откатывайте миграции в продакшене; выпускайте исправление вперёд. Подписка остаётся валидной,
потому что URL не меняется.

Если упала сама миграция, отката образов не будет: схема уже сдвинута, и старый код поверх неё
ломается тише, чем простой. Скрипт печатает путь дампа — восстановление из него осознанное решение
с `CONFIRM_RESTORE=yes`, см. [backup.md](backup.md).

## Бэкап

Ежедневный таймер запускает `scripts/backup.sh`; см. [backup.md](backup.md). Деплой не заменяет
политику бэкапа: проверьте таймер и одни учения восстановления до первого реального сотрудника.

Отдельный дамп на время выката существует только для пути сбоя: он снят при живых старых процессах,
поэтому не является согласованным снимком и никогда не грузится в S3 и не чистится по ретеншну.

## После деплоя

Запишите версию и результат смоука в `docs/measurements/`, если деплой меняет измеренное число.
Если что-то сломалось, пишите `docs/incidents/` в тот же день.
