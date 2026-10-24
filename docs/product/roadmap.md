---
title: 'План доводки бота до идеального состояния'
summary: 'Что осталось сделать после живого прогона: приоритеты, файлы, гейты и время. Без новых eval-прогонов.'
kind: продукт
owner: p4ulbr4dl3y
status: черновик
last_verified: 2026-10-24
---

# План доводки бота

Основание — живой прогон 24.10.2026 (`docs/measurements/2026-10-24-live-max-e2e-full-scenario.md`):
сценарий пройден до `done`, одиннадцать дефектов закрыто. Здесь то, что осталось.

Правила игры те же: контракт раньше кода, тексты в `docs/product/copy.yaml`, числа только в
`docs/measurements/`. Новые eval-прогоны не планируются: приёмка идёт существующими тирами
(`pytest -m "not eval"`, `pytest -m integration`, `scripts/channel_smoke.py`) и живой проверкой в MAX.

## Приоритет 1 — доверие к боту (обязательно)

| # | задача | файлы | гейт |
|---|---|---|---|
| 1.1 | Деплой фиксов и повторный живой прогон: файл без подписи, файл с подписью-вопросом, вопрос после `done` | CI по SHA, `docs/runbooks/deploy.md` | живой диалог: `inbound_files.status=stored`, вопрос в `questions` |
| 1.2 | Подтверждения шага не только словами: кнопка «Готово» на каждом `wait`-шаге, где ждём текст | `docs/contracts/scenario.schema.json` (поле уже есть — `keyboard`), `scenarios/*.yaml` | `pytest apps/api/tests/test_scenario.py`, живой прогон |
| 1.3 | «Что мне сейчас нужно сделать?» — повтор шага с прогрессом («Шаг 3 из 21») и кнопкой дальше | `core/transitions.py`, `docs/product/copy.yaml` | `test_service.py::test_a_question_about_the_current_stage_repeats_the_step` |
| 1.4 | Резюме ответа опроса: «Записал: 8 из 10» одной строкой | `core/transitions.py`, `copy.yaml` | `test_transitions.py`, живой опрос |
| 1.5 | После `done` — не тупик: короткое меню (льготы, кабинет, `/reboot`) | `copy.yaml`, `service._after_run` | `test_service.py::test_help_and_next_stage_work_after_completion` |
| 1.6 | Ограничить демо-команды `--live`: `/reboot`, `/nextStage` только для роли демо-аккаунта | `api/webhook`, `service.handle`, `docs/product/roles.md` | `test_app.py`, живой прогон с обычного аккаунта |

## Приоритет 2 — скорость и ясность

| # | задача | файлы | гейт |
|---|---|---|---|
| 2.1 | Мгновенный ответ на частые вопросы (столовая, пропуск, аванс, ноутбук) без похода в модель: короткий FAQ-слой поверх индекса | `app/worker/answerer.py`, `knowledge/` | `test_answerer.py`, живой замер `latency_ms` |
| 2.2 | Предзагрузка картинок шагов на старте воркера (сейчас аплоад 0.8–1.4 с на сообщение, кеш ленивый) | `app/channels/max/media.py`, `app/worker/*` | `test_channel_smoke.py`, лог `uploads` |
| 2.3 | Уведомление об этапе без спама: одно сообщение + кнопка «Напомнить сейчас» | `copy.yaml`, `core/transitions.py` | `test_transitions.py` |
| 2.4 | Единый формат ответа: цитата → вывод → «Следующий шаг» (сейчас три абзаца вперемешку) | `docs/prompts/**`, `answer-policy.md` | `test_grounding.py`, выборочно 10 живых вопросов |

## Приоритет 3 — кабинет и обратная связь

| # | задача | файлы | гейт |
|---|---|---|---|
| 3.1 | Экран «Пробелы в базе знаний»: топ вопросов с `no_sources` (26 из 76 за прогон) | `admin/queries.py`, `apps/admin/` | `test_admin_api.py`, `scripts/verify_demo.sh` |
| 3.2 | В карточке сотрудника — прогресс «шаг 7 из 21» и дата следующего этапа | `admin/queries.py`, контракт `admin-api.md` | `test_admin_contract.py` |
| 3.3 | Пометка «вопрос отвечен человеком» видна в диалоге (мягкая реплика в чат) | `admin/actions.py`, `copy.yaml` | `test_admin_api.py` |

## Приоритет 4 — устойчивость

| # | задача | файлы | гейт |
|---|---|---|---|
| 4.1 | Ретрай файла: `inbound_files.status=failed` повторяется по кнопке в кабинете | `admin/actions.py`, `app/files/intake.py` | `test_inbound_files.py` |
| 4.2 | Напоминание за 1 час до этапа вместо тишины в 48 ч ожидания | `scenarios/*.yaml` (`timeout`), `scheduler` | `test_integration_db.py::test_scheduler_enqueues_a_due_reminder` |
| 4.3 | Метрики в кабинет: `latency p95`, `no_sources rate`, `escalations/day` | `admin/queries.py` | `test_admin_api.py` |

## Чего не делаем

- Новых eval-наборов и прогонов: времени нет, качество проверяем живым диалогом и юнит-гейтами.
- Новых каналов (Telegram, VK) — только после пилота в MAX.
- OCR входящих документов: ADR 0027 фиксирует отказ.
- Переписывания принятых ADR: только новый ADR с `supersedes`.

## Порядок работ

1. 1.1 (деплой и живая приёмка файлов) — блокирует остальное.
2. 1.2–1.6 — один спринт, каждая задача = коммит + тест + живая проверка.
3. 2.1–2.2 — измеримый выигрыш по `latency_ms`; 2.3–2.4 — тексты и тон.
4. 3.x — кабинет, после стабильного диалога.
5. 4.x — по остатку времени.

## Приёмка плана

`make check` зелёный, живой диалог проходит сценарий до `done`, файл с подписью-вопросом даёт
ответ и не повторяет этап, вопрос после `done` получает ответ, в кабинете видны пробелы в базе.
