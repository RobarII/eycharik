# Run the cron pass

The worker owns the real-time loop. A separate cron entrypoint exists because schedules in the
client's infrastructure are cron jobs, and a process that exits is easier to alert on than a
daemon that silently stops.

```bash
make cron                       # one pass, then exit
uv run python -m onboarding.app.scheduler --max-jobs 200
```

One pass does three things, in this order:

1. `ReminderScheduler.tick()` — turns every active run whose `reminder_at` is due into a `timeout`
   job, and clears the timestamp so a second pass cannot duplicate it.
2. `JobRunner.run_once()` in a loop until the queue is empty or `--max-jobs` is reached.
3. `MessageDispatcher.run_once()` — delivers the outbox to MAX with backoff.

Every step is idempotent across passes: the reminder timestamp is cleared under the same row lock
that selects it, jobs are claimed with `FOR UPDATE SKIP LOCKED`, and outbox delivery records the
MAX message id.

## Crontab

```cron
* * * * * cd /srv/onboarding && /usr/bin/env uv run python -m onboarding.app.scheduler >> /var/log/onboarding-cron.log 2>&1
```

Use a lock so a slow pass cannot overlap the next one:

```cron
* * * * * flock -n /tmp/onboarding-cron.lock sh -c 'cd /srv/onboarding && uv run python -m onboarding.app.scheduler'
```

## Verify

```bash
make cron                                   # expect "cron pass: reminders=N jobs=N messages=N"
psql "$DATABASE_URL" -c "select kind, status, count(*) from jobs group by 1, 2"
psql "$DATABASE_URL" -c "select status, count(*) from messages group by 1"
```

- `jobs.status = 'running'` and older than five minutes: a pass died mid-job. The worker retries
  with backoff up to five attempts; after that the row is `failed` and visible in the audit log.
- Exit code is non-zero only on a crash. A pass that finds nothing to do exits `0` and logs zeros.
