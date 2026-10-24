---
title: 'Проверка 2026-10-24: весь сценарий адаптации в живом MAX'
summary: 'Сценарий пройден от welcome до done с кнопками, опросами и /nextStage; найдено десять дефектов, все закрыты и покрыты тестами.'
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Проверка 2026-10-24 — полный сценарий в живом MAX

- дата: `2026-10-24`
- окружение: `production`, `https://bot.state3407.space`, VPS `85.208.9.104`, `/opt/onboarding`,
  контейнеры `api`, `worker`, `postgres`, `admin` — healthy; канал `max`, `CHANNELS=max`;
  вход в диалог — юзербот `PyMax` из аккаунта сотрудника (`~/.pymax/user.db`, профиль `502781191`),
  чат с ботом `278874685`, бот `224960314`
- коммит: `5f20846` (образ прода); фиксы по итогам — `ba8f858`, `c57ff31`, `6183acf`,
  порядок и маршрутизация — `f26aafb`
- команда: `~/.pymax/venv/bin/python /tmp/e2e_max.py send|read`, нажатие кнопки через
  `MSG_SEND_CALLBACK` (opcode `118`) с `callbackId` из `InlineKeyboardAttachment`,
  `ssh vps docker exec onboarding-postgres-1 psql` для сверки состояния на каждом шаге
- набор: employee `1001`, прогон `c343ad52`; кейсы — `2026-10-24-live-max-e2e-full-scenario.jsonl`

До прогона: `runs=8`, `events=168`, `jobs=168`, `messages=240`, `questions=67`, `inbound_files=0`.
После: `runs=10`, `events=256`, `jobs=256`, `messages=338`, `questions=76`, `inbound_files=1`.
Латентность ответа по базе за прогон: `avg 4471 ms`, `max 10676 ms`, `n=9`.

## Что проверено вживую

| шаг | действие | проверка | проход |
|---|---|---|---|
| `welcome` | кнопка `tone_formal` после вопроса по корпусу | тон `formal`, шаг -> `documents_checklist` | да |
| `documents_checklist` | текст «Я отправил документы вчера вечером» | шаг -> `day_before` | да |
| `day_before` | `/nextStage`, затем кнопка `not_ready` | `day_before_questions`, приглашение задать вопрос | да |
| `day_before_questions` | вопрос «Во сколько приходить и куда идти?» | ответ с цитатой `hr/onboarding-first-day#0` | да |
| `day_before_questions` | «готово» | шаг -> `first_day` (отложен на сутки) | да |
| `day_three_survey` | кнопка `q_tasks_clear_partly`, оценка `8`, открытый ответ | три ответа, `question_index` 0->2, шаг -> `week_two_plan` | да |
| `week_two_survey` | оценка `5` -> вопрос причины -> текст причины, далее восемь `9` | `pending_reason=tasks_clear`, 13 ответов, шаг -> `month_two_plan` | да |
| `month_two_survey` | `7`, затем три открытых ответа | 17 ответов, шаг -> `probation_reminder` | да |
| `probation_survey` | кнопка `q_probation_result_no`, кнопка `q_stay_intent_unsure` | шаг -> `done`, `status=completed` | да |
| `done` | «Адаптация завершена» | `runs.status=completed`, `outcome=completed` | да |
| идемпотентность | повторное нажатие старой кнопки | повтор вопроса, ответ не записан дважды | да |

## Найденные дефекты

| № | дефект | доказательство | фикс |
|---|---|---|---|
| 1 | сообщения уходят не по порядку: интро опроса после первого вопроса, уведомление об этапе раньше самого этапа | `messages` 298/299 (`sent_at` 21:30:51.347 против 21:30:50.699), 303/304 | `_claim` сортирует строки по `id` |
| 2 | подтверждение («Понятно») на этапе в расписании повторяет уведомление об этапе | шесть подряд «Следующий этап…» в одном диалоге | молчаливое подтверждение, уведомление только на кнопку |
| 3 | текстовый ответ на `choice` («Пока не уверен») отклоняется | вопрос повторён, `answers` не вырос | `_choice` сверяет и текст варианта |
| 4 | `11` и `abc` на шкале повторяют вопрос без объяснения | два одинаковых промпта подряд | подсказка `invalid_answer` в `docs/product/copy.yaml` |
| 5 | эмодзи уходит в HR как вопрос без ответа | `questions` 72, `🙂`, `reason=no_sources` | проверка `has_words` |
| 6 | «Что мне сейчас нужно сделать?» -> «не нашёл ответа, передал HR» | `questions` 73, `reason=no_sources` | `asks_about_stage` повторяет текущий шаг |
| 7 | после `done` бот молчит на вопросы | задачи 244/245 `done`, ни одного исходящего | `_after_run` отвечает через `Answerer` |
| 8 | после `done` не работают `/help` и `/nextStage` | оба сообщения без ответа | команды обрабатываются и без активного прогона |
| 9 | файл не скачивается: `fd.oneme.ru` вне списка хостов | `inbound_files.status=failed`, `FileFetchError: untrusted_host` | `ba8f858` |
| 10 | подпись-вопрос к файлу теряется, этап объявляется дважды | `messages` 258 и 261, вопроса нет в `questions` | `c57ff31` |

## Гейты после фиксов

| гейт | результат |
|---|---|
| `ruff check apps/api` | All checks passed |
| `mypy` | Success: no issues found in 155 source files |
| `pytest -m "not integration and not eval"` | 1026 passed |
| `pytest -m integration` | 76 passed |
| `make docs` | docs-index ok: 142 документов, docs ok |

Фиксы 1, 2, 3, 5, 6, 7, 8 в боевом образе не проверены: прод собран из `5f20846`, выкладка идёт
через CI по SHA (`docs/runbooks/deploy.md`). Повторный живой прогон нужен после деплоя; отдельно
остаётся проверить приём файлов с подписью-вопросом.
