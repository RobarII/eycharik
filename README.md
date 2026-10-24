# Ассистент онбординга в MAX

ИИ-ассистент онбординга сотрудников в мессенджере MAX: сценарии онбординга для новичков,
кабинет рекрутёра и ассистент по базе знаний компании, который отвечает только обоснованно.

Сделан для кейса «ИИ-ассистент в MAX» (ООО «Группа ПОЛИПЛАСТИК»).

## Карта

| Путь | Что | Меняется |
|---|---|---|
| `docs/` | архитектура, контракты, решения, прогоны, оценки | да |
| `knowledge/` | закрытый корпус компании, из которого отвечает ассистент | да, с проверкой владельца |
| `apps/api/` | сервис: webhook API, движок сценариев, RAG, admin API | да |
| `apps/admin/` | кабинет рекрутёра | да |
| `docs/evals/` | золотой набор и контракт его прогонщика | да |
| `infra/demo/` | демо-сотрудники для `make seed` | да |

## С чего начать

| Вопрос | Файл |
|---|---|
| Как проверить работу за десять минут? | `docs/checker.md` |
| Что строим и зачем? | `docs/architecture.md` |
| Как работать в этом репозитории? | `AGENTS.md` |
| Где живёт факт? | `docs/README.md` |
| Что бот может отвечать? | `docs/product/answer-policy.md` |

## Проверить за десять минут

```bash
make doctor       # чего не хватает на машине; ничего не запускает
make verify       # гейт: линт, типы, импорты, тесты, покрытие, доки, кабинет
make demo         # стек + демо-набор, печатает URL и токен
```

`make verify` без `ONBOARDING_TEST_DATABASE` останавливается и говорит, как поднять базу: гейт без
интеграционного тира ничего не доказывает. `make verify-demo` сверяет демо-счётчики, обещанные в
`docs/product/demo-script.md`; качество ответов он не проверяет — для этого нужен `make eval` с
ключом. Подробный маршрут и ожидаемый вывод — в [docs/checker.md](docs/checker.md).

Ключ модели не нужен: демо отвечает детерминированным провайдером. Живые модели, включая
бесплатный тир OpenRouter, — там же.

## Docker Compose: пусто, демо, снова пусто

`docker compose up -d --build` поднимает PostgreSQL, миграции, api, воркер и статический
кабинет. Сидов нет намеренно: база пустая, поэтому после входа кабинет показывает нулевые
счётчики и пустые списки.

Откройте <http://localhost:3000> и войдите с `dev-hr-token` (или `dev-recruiter-token` для
скоупа рекрутёра).

Умолчания compose — локальный офлайн-профиль (ответы от `extractive`-провайдера, хеширующие
эмбеддинги) и демо-токены администратора. Для потока «пусто/демо» файл `.env` не нужен. Чтобы
включить настоящие модели и MAX, скопируйте `.env.example` в `.env` и задайте ключи.

### Наполнить демо-данными

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

### Убрать демо-данные

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

### Полный сброс

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

## Состояние

Работает от начала до конца на локальном Postgres с pgvector и внешней моделью через OpenRouter:

- **Вебхук MAX**: проверка секрета, дедупликация `events`, надёжная постановка задачи в
  очередь, `200` за миллисекунды.
- **Движок сценариев**: версионированный YAML, закреплённый за прогоном, кнопки, напоминания,
  опросы со шкалой на 10 баллов, эскалация по таймауту. Двадцать шагов от приветствия до конца
  испытательного срока. Ветку выбирает строка сотрудника, поэтому заводской вариант
  (`onboarding_plant`) живой, а не мёртвый контент: свой текст про транспорт и без вопроса про
  удалённую работу. Приветствие спрашивает «ты» или «вы»; выбор хранится в прогоне и
  переключает текст следующих шагов.
- **Поиск**: корпус с frontmatter и JSON Schema, детерминированная нарезка, pgvector HNSW плюс
  русский `tsvector`, RRF, внешнее переранжирование, аудитория и срок как предикаты SQL. Каждый
  ответ несёт цитату из найденного набора или уходит в эскалацию.
- **Ответы**: один вызов модели, JSON-контракт, версия промпта `v7`; личные вопросы («кто мой
  наставник», зарплата, договор) уходят в эскалацию, а не получают ответ общей политикой.
- **Радар рисков**: после каждого опроса ответ классифицируется (внешняя модель с
  детерминированным запасным вариантом по совпадению слов), правила превращают сигналы в
  уровень, теги и русские причины, а журнал аудита пишет `risk_assessed` / `risk_escalated`.
  Кабинет показывает обзор за семь дней и недельный дайджест сигналов, которым нужен человек.
- **Кабинет рекрутёра**: прогоны, карточка сотрудника с хронологией аудита, очередь вопросов со
  скоупом по рекрутёру, менеджеру (по подразделению) или HR; ответ закрывает вопрос и уходит
  через `outbox`; HR может вывести сотрудника; HR может загрузить, открыть и править документ
  базы знаний с проверкой frontmatter.
- **Сроки хранения**: просроченные вопросы, загрузки, сообщения `outbox` и персональные поля
  аудита чистит воркер раз в час; политика задаётся `DATA_RETENTION_DAYS`; вывод сотрудника
  мгновенный и попадает в аудит. Арендованная строка `outbox` держит аренду, поэтому упавший
  воркер не теряет сообщение.
- **Планировщик**: cron-точка входа делит строительные блоки с воркером, поэтому напоминания и
  `outbox` разбираются, даже когда работает только периодическая задача.

![Радар рисков](docs/assets/cabinet-risk.png)

| Что | Где смотреть |
|---|---|
| Качество и цена полного набора, настоящая модель | [docs/measurements/current.md](docs/measurements/current.md) |
| Задержка: оба гейта провалены, это записано | там же |
| Поиск на хешах без ключа — диагностика, не качество | там же |
| Тесты | `apps/api/tests/` |

Числа живут только в `docs/measurements/`: README их не переписывает, поэтому и не врёт, когда
прогон обновится. Ранние прогоны на маленьком наборе несравнимы с нынешним.

![Карточка прогона](docs/assets/cabinet-run.png)

![Список прогонов](docs/assets/cabinet-runs.png)

![База знаний](docs/assets/cabinet-knowledge.png)
