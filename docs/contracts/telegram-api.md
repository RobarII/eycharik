---
title: Контракт Telegram Bot API
summary: Какие факты Telegram Bot API использует интеграция и откуда каждый из них взят.
kind: контракт
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Контракт Telegram Bot API

Всё, на что опирается интеграция, с источником каждого факта. Если Telegram меняет поле, этот файл меняется тем же коммитом, что и адаптер.

Источник: <https://core.telegram.org/bots/api> и <https://core.telegram.org/bots/faq> (прочитано 2026-10-26).

## Подключение

| Факт | Значение |
|---|---|
| Базовый URL | `https://api.telegram.org/bot<token>/<method>` |
| Аутентификация | токен — часть URL; заголовка `Authorization` нет |
| Тип содержимого | `application/json` для каждого метода ниже |
| Регистрация вебхука | `setWebhook` с `url` и `secret_token` |
| Аутентификация входящих | заголовок `X-Telegram-Bot-Api-Secret-Token` на каждой доставке |

## Эндпоинты, которые реализует адаптер

| Метод | Путь | Назначение |
|---|---|---|
| `POST` | `sendMessage` | отправить сообщение, необязательный `reply_markup` |
| `POST` | `editMessageText` | переписать отправленное сообщение |
| `POST` | `setWebhook` | регистрация, `onboarding.cli webhook --channel telegram` |

`sendMessage`: `chat_id`, `text` 1–4096 символов после разбора сущностей, `parse_mode` (`MarkdownV2` или `HTML`), `reply_markup` с `inline_keyboard`, `reply_to_message_id`.

`sendPhoto` (`photo` как `file_id` или multipart-загрузка, `caption` до 1024 символов) описан, но не реализован: `OutboundMessage` пока не несёт изображение, поэтому адаптер отправляет текст и клавиатуру. Его добавление — сначала правка значения сообщения, а не этого адаптера.

`InlineKeyboardButton.callback_data`: `String` от 1 до 64 байт. Длиннее — ошибка, не обрезка.

## Обновления

| Поле `update` | Наше событие |
|---|---|
| `message.text`, начинающийся с `/start` | `EMPLOYEE_CREATED` |
| `message.text` | `MESSAGE_RECEIVED` |
| `callback_query.data` | `BUTTON_PRESSED` |
| `message.document` | `FILE_RECEIVED` с `file_id`; байты не скачиваются — в update нет URL, для этого нужен отдельный вызов `getFile` |

`update_id` — ключ дедупликации. `message.chat.id` — чат; `from.id` — отправитель, и в группах они различаются.

## Лимиты частоты

Telegram документирует «no more than about 30 messages per second» суммарно и «not more than one message per second in a single chat». Профиль задаёт `messages_per_second: 30` и `per_chat_per_second: 1`, и адаптер держит темп по обоим. `429` — это `ChannelUnavailableError`: диспетчер отступает, и строка возвращается в `pending`. Поле `retry_after` не учитывается — backoff наш, так что один путь кода покрывает каждый мессенджер.

## Отличия от MAX, которые важны

- Бот не может начать беседу: сообщение пользователю, который никогда не нажимал `/start`, падает с `403: bot can't initiate conversation with a user`. Это совпадает с гейтом привязанной идентичности: прогон стартует с `/start`, никогда не с нашей стороны.
- `parse_mode` — диалект. `MarkdownV2` требует экранирования ``_*[]()~`>#+-=|{}.!``; рендерер экранирует, текст остаётся простым.
- Правки заменяют `text` и `reply_markup` вместе; правка без разметки её удаляет.

## Ещё не снято

Фикстуры payload синтетические, настоящий update не снят. Правило то же, что в `max-api.md`.
