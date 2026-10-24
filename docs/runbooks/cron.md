---
title: Прогон по cron
summary: Как устроен отдельный cron-вход и как проверить один проход планировщика.
kind: прогон
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Прогон по cron

Воркер владеет циклом реального времени. Отдельная точка входа для cron существует потому, что
расписания в инфраструктуре клиента — это cron-задачи, а процесс, который завершается, проще
поставить под алерт, чем демон, который молча умирает.

```bash
make cron                       # one pass, then exit
uv run python -m onboarding.app.scheduler --max-jobs 200
```

Один проход делает три вещи, в таком порядке:

1. `ReminderScheduler.tick()` — превращает каждый активный прогон с наступившим `reminder_at` в
   задачу `timeout` и очищает отметку времени, чтобы второй проход не задвоил её.
2. `JobRunner.run_once()` в цикле, пока очередь не опустеет или не упрётся в `--max-jobs`.
3. `MessageDispatcher.run_once()` — доставляет `outbox` в MAX с бэкоффом.

Каждый шаг идемпотентен между проходами: отметка напоминания очищается под той же блокировкой
строки, которой она выбирается, задачи забираются через `FOR UPDATE SKIP LOCKED`, а доставка из
`outbox` записывает id сообщения MAX.

## Crontab

```cron
* * * * * cd /srv/onboarding && /usr/bin/env uv run python -m onboarding.app.scheduler >> /var/log/onboarding-cron.log 2>&1
```

Берите блокировку, чтобы медленный проход не наложился на следующий:

```cron
* * * * * flock -n /tmp/onboarding-cron.lock sh -c 'cd /srv/onboarding && uv run python -m onboarding.app.scheduler'
```

## Проверка

```bash
make cron                                   # expect "cron pass: reminders=N jobs=N messages=N"
psql "$DATABASE_URL" -c "select kind, status, count(*) from jobs group by 1, 2"
psql "$DATABASE_URL" -c "select status, count(*) from messages group by 1"
```

- `jobs.status = 'running'` и старше пяти минут: проход умер на задаче. Воркер повторяет с бэкоффом
  до пяти попыток; дальше строка `failed` и видна в аудите.
- Код выхода ненулевой только при падении. Проход, которому нечего делать, выходит с `0` и пишет
  нули в лог.
