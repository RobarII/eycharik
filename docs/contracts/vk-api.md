---
title: Контракт VK Callback API
summary: Какие факты VK Callback API использует интеграция и откуда каждый из них взят.
kind: контракт
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Контракт VK Callback API

Всё, на что опирается интеграция, с источником каждого факта. Если VK меняет поле, этот файл меняется тем же коммитом, что и адаптер.

Источник: <https://dev.vk.com/ru/api/callback/getting-started> и <https://dev.vk.com/ru/method/messages.send> (прочитано 2026-10-26).

## Подключение

| Факт | Значение |
|---|---|
| Входящие | VK постит JSON на callback URL, настроенный для сообщества |
| Подтверждение | на payload с `"type": "confirmation"` нужно ответить кодом подтверждения, простым текстом |
| Аутентификация входящих | поле `secret` каждого payload, когда секрет настроен; иначе его нет |
| Исходящие | `https://api.vk.com/method/messages.send` с `access_token` и `v` |

Каждое событие несёт `type`, `group_id` и `event_id`. `event_id` — ключ дедупликации.

## Эндпоинты, которые реализует адаптер

| Метод | Назначение |
|---|---|
| `messages.send` | отправить сообщение с необязательными `keyboard` и `attachment` |
| `messages.edit` | переписать сообщение, отправленное сообществом |

`messages.getLongPollServer`, `photos.getMessagesUploadServer` и подобные описаны, но не используются: `OutboundMessage` пока не несёт изображение.

`messages.send`: `peer_id`, `message` до 4096 символов, `random_id` (обязателен: VK отбрасывает повтор с тем же значением), `keyboard` (JSON, см. ниже), `attachment` (для изображений).

## События

| Payload | Наше событие |
|---|---|
| `message_new`, `object.message.text`, начинающийся с `/start` | `EMPLOYEE_CREATED` |
| `message_new` | `MESSAGE_RECEIVED` |
| `message_event` (кнопка-колбэк) | `BUTTON_PRESSED` |

`object.message.peer_id` — чат; `from_id` — отправитель. В `message_event` `peer_id` и `user_id` — отдельные поля, а `payload` несёт id кнопки.

VK повторяет доставку, не подтверждённую `ok` в свой таймаут. `event_id` вместе с первичным ключом `events` делает повтор безвредным.

## Клавиатура

`keyboard` — JSON-объект: `one_time`, `inline` и `buttons` — до 10 рядов по 5 кнопок. Кнопка — `{"action": {"type": "callback", "label": "...", "payload": "..."}}`; `payload` — не больше 255 символов.

Два следствия, которые кодирует профиль:

- `keyboard_scope: dialog` — клавиатура принадлежит беседе, а не одному сообщению. Новое сообщение без `keyboard` оставляет старую на месте; чтобы её убрать, нужна явная пустая клавиатура.
- `inline: true` принимается только для сообщений от сообщества, а кнопка-колбэк срабатывает, только когда у сообщества включена поддержка колбэков.

## Лимиты частоты

VK документирует лимит около 20 запросов в секунду на метод для токена сообщества. Профиль задаёт `messages_per_second: 20` и оставляет `per_chat_per_second: null`: документированного правила по чату нет. `429` или код ошибки 6 (`Too many requests per second`) — это `ChannelUnavailable`.

## Ещё не снято

Фикстуры payload синтетические, настоящий колбэк не снят. Проверьте лимит частоты и ограничение `inline` против настроек сообщества, прежде чем включать канал в продакшене.
