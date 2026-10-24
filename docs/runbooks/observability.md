---
title: Наблюдаемость
summary: Что процесс отдаёт в метриках, по каким порогам ставить алерты и что сознательно не собирается.
kind: прогон
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Наблюдаемость

Что процесс отдаёт, по чему ставить алерты и что он сознательно не собирает.

## Что отдаётся

`GET /metrics` возвращает текстовый формат Prometheus. Когда `METRICS_TOKEN` задан, эндпоинт
требует `Authorization: Bearer <token>` и иначе отвечает `401`; когда пуст — открыт, как `/healthz`,
что допустимо только для локального демо. Продакшен отказывается стартовать без `METRICS_TOKEN`, а
nginx хоста отдаёт `/metrics` только на loopback.

| метрика | тип | метки | смысл |
|---|---|---|---|
| `onboarding_http_requests_total` | counter | `method`, `route`, `status` | запросы по шаблону роута; неизвестные пути схлопываются в `unmatched` |
| `onboarding_http_request_seconds` | histogram | `method`, `route` | задержка запроса |
| `onboarding_answer_total` | counter | `reason`, `escalated` | ответы по вердикту обоснованности |
| `onboarding_answer_stage_seconds` | histogram | `stage` = `retrieval`, `rerank`, `generate` | задержка конвейера, та часть, которую вебхук не видит |
| `onboarding_answer_citations` | histogram | — | цитат на ответ |
| `onboarding_llm_tokens_total` | counter | `direction` = `input`, `output` | расход у провайдера |
| `onboarding_answer_cost_rub_total` | counter | — | стоимость ответа по токенным ценам провайдера |

Каждый не-health запрос получает заголовок ответа `X-Request-ID` и одну JSON-строку лога
`{"event":"http_request",...}`. Работа вебхука идёт асинхронно; связывайте её через аудит-лог, где
те же поля `answer_completed` плюс id прогона и сотрудника.

Метрики считаются по процессу. При двух репликах `api` скрейпер суммирует счётчики; гистограммам
нужен `histogram_quantile` по каждому инстансу, затем максимум по инстансам, либо настоящий бэкенд
метрик.

## По чему ставить алерты

Пороги — политика, а не измерение. Бюджет задержки — 8000 ms (ADR 0009); p95 в оценках записан в
`docs/measurements/`.

```promql
# 95% of answer-stage time above 8 s for 10 minutes
histogram_quantile(0.95,
  sum by (le, stage) (rate(onboarding_answer_stage_seconds_bucket[10m]))
) > 8

# the assistant is escalating instead of answering
sum(rate(onboarding_answer_total{escalated="true"}[10m]))
  /
sum(rate(onboarding_answer_total[10m])) > 0.30

# provider calls are failing before an answer exists
rate(onboarding_http_requests_total{status=~"5.."}[5m]) > 0

# spend is running away
increase(onboarding_answer_cost_rub_total[1h]) > 100
```

Первые два — продуктовые сигналы: задержка и отказ. Всплеск 5xx на `/webhook/max` — проблема
доставки MAX, не ответов.

## Что не собирается

- Ни текста вопроса, ни id сотрудника, ни id чата, ни названия документа в метках. И
  кардинальность, и персональные данные остаются вне эндпоинта метрик.
- Ни тел промптов, ни тел ответов в логах. Аудит-лог уже хранит минимум для радара риска, по
  политике хранения в `docs/product/roles.md`.
- Внешнего трейсинга пока нет. Трейс требует коллектора и политики сэмплирования; гистограмма по
  стадиям — дешёвый первый шаг и отвечает на тот же вопрос о задержке.

## Локальная проверка

```bash
make run
curl -s -H "Authorization: Bearer $METRICS_TOKEN" localhost:8000/metrics | grep onboarding_answer
```

Для локального процесса с пустым `METRICS_TOKEN` заголовок не нужен; продакшен без него не
стартует.

Если вывод пуст, в этом процессе ещё не было ни одного ответа. `/metrics` и `/healthz` не пишутся в
лог, чтобы журнал доступа оставался читаемым.
