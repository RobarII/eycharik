---
title: Хранение и офбординг
summary: Что система хранит, сколько и как проверить, что чистка прошла.
kind: прогон
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Прогон: хранение и офбординг

Что система хранит, как долго и как проверить, что чистка прошла.

## Что покрыто

| Данные | Где | Хранение |
|---|---|---|
| Вопросы в эскалации и ответы | `questions` | `DATA_RETENTION_DAYS` после `asked_at` |
| Ответы, написанные в кабинете | `questions.resolution` | как у вопроса |
| Текст исходящих сообщений (включая ответы) | `messages` outbox | доставленные строки после `sent_at` + окно; недоставленные после `created_at` + окно; офбординг сразу удаляет все строки по чатам сотрудника |
| Документы, присланные в чат (сканы паспорта и т. п.) | `inbound_files` | байты под AES-256-GCM; удаляются после `created_at` + окно и сразу при офбординге; без `INBOUND_FILES_KEY` не сохраняются |
| Персональные поля в аудите (`evidence`, `quote`, `question`, `text`) | `audit_log.fields` | заменяются на null после `DATA_RETENTION_DAYS`; строка остаётся |
| Прогоны, сигналы риска, задачи, события | `runs`, `risk_*`, `jobs`, `events` | не чистятся; в них id, не свободный текст |
| Документы базы знаний | `kb_*` | не персональные данные; версионируются по `valid_from` / `valid_to` |

`DATA_RETENTION_DAYS` по умолчанию 365, должен быть не меньше 1 и читается при старте процесса. Это
значение политики: меняйте его в окружении деплоя, не в базе.

## Офбординг сотрудника

Только HR. Вызов идемпотентен: второй `DELETE` возвращает нулевые счётчики и `200`.

```bash
curl -X DELETE "https://$HOST/admin/api/employees/$EMPLOYEE_ID" \
  -H "Authorization: Bearer $HR_TOKEN"
```

Ожидаемый ответ: `{"employee_id": "...", "questions_deleted": 3, "messages_deleted": 2, "runs_closed": 1, "audit_redacted": 7, "files_deleted": 2}`.
Сотрудник исчезает из справочника и из всех списков по скоупу; строка остаётся с `status='left'` и
`left_at`. `files_deleted` считает присланные в чат документы: скан паспорта уходит вместе с
перепиской, а не лежит до общего срока ([ADR 0027](../decisions/0027-inbound-documents-are-encrypted.md)).

## `outbox` — это очередь

`messages` не архив. Взятая строка держит аренду в `available_at`; воркер, который умер между
взятием и отправкой, оставляет `status='sending'`, и следующий проход диспетчера возвращает её в
`pending`, когда аренда истечёт. Дальше проход хранения применяет одно правило:

- `sent`: удалить, когда `sent_at` (или `created_at`, если у легаси-строки нет `sent_at`) вне окна;
- `pending`, `sending`, `failed`: удалить, когда `created_at` вне окна; недоставленное сообщение
  годовой давности не понадобится никогда.

Удаление идёт пакетами (`LIMIT` на каждый оператор), поэтому большой первый проход не держит одну
длинную блокировку. Проход пишет `messages_deleted`, `files_deleted` и `inbound_files_deleted` в
`retention_purged`.

## Как идёт чистка по расписанию

- Воркер: раз в час, рядом с тиком планировщика.
- Точка входа для cron (`python -m onboarding.scheduler`): раз за тик, после разбора `outbox`.
- Каждый проход пишет `retention_purged` в `audit_log` со счётчиками удалённых строк и
  обнулённых полей.

Проход можно смело повторять: он удаляет по отсечке, а обнуление трогает только ещё присутствующие
поля.

## Проверка

```sql
-- oldest retained question; should be newer than now() - DATA_RETENTION_DAYS
select min(asked_at) from questions;

-- audit rows still carrying personal fields past the window; should return 0
select count(*) from audit_log
where created_at < now() - interval '365 days'
  and fields ?| array['evidence', 'quote', 'question', 'text'];

-- chat documents past the window; should return 0
select count(*) from inbound_files
where created_at < now() - interval '365 days';

-- outbox rows past the window; should return 0 for sent rows and 0 for undelivered rows
select status, count(*)
from messages
where (status = 'sent' and coalesce(sent_at, created_at) < now() - interval '365 days')
   or (status in ('pending', 'sending', 'failed')
       and created_at < now() - interval '365 days')
group by status;

-- recent purge passes
select created_at, fields
from audit_log
where name = 'retention_purged'
order by created_at desc
limit 5;
```

Если первый запрос старше окна, воркер не работает или проход падает; читайте лог воркера по
`retention` и строки `retention_purged`. Если запрос по аудиту даёт не ноль, значит имя поля
добавили в событие аудита, но не добавили в `PERSONAL_AUDIT_KEYS` в
`apps/api/onboarding/core/retention.py`. Строки в `sending` с `available_at` в будущем внутри живой
аренды; строки с прошедшим `available_at` забирает следующий проход диспетчера.

## Замечания

- Этот ранбук описывает механизм, а не юридическую достаточность окна. Сроком хранения владеет
  политика защиты данных компании; 365 дней — заглушка, которую надо подтвердить до продового
  деплоя.
- Входящие документы — самый чувствительный класс данных здесь. Их байты шифруются ключом
  развёртывания, а не только диском; потеря `INBOUND_FILES_KEY` означает потерю скачивания, и это
  записано как цена решения (ADR 0027).
- Офбординг делается сразу и необратим. Экспортируйте всё, что требует политика, до вызова `DELETE`.
