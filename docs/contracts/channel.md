---
title: Контракт канала
summary: Где проходит граница между доменом и мессенджером и что обязан выполнять адаптер канала.
kind: контракт
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Контракт канала

Граница между доменом и мессенджером. Всё здесь нормативно: адаптер мессенджера, который это нарушает, валит `tests/test_channel_contract.py`.

Решено в [ADR 0019](../decisions/0019-a-channel-is-an-address.md). Лимиты по мессенджерам лежат в `apps/api/channel-profiles/<channel>.yaml` и проверяются схемой [channel-profile.schema.json](channel-profile.schema.json).

## Значения

| Значение | Смысл |
|---|---|
| `Channel` | `max`, `telegram`, `vk`. `StrEnum` в `onboarding.core.models`. |
| `Address(channel, chat_id)` | Где находится беседа. Хранится на прогоне, строке `outbox` и строке вопроса. |
| `EmployeeId` | Человек в справочнике компании. Никогда не id пользователя мессенджера. |

Отправитель отображается в сотрудника через `channel_identities(channel, external_id) -> employee_id`. Вебхук разрешает это один раз, на входе. Непривязанный отправитель отклоняется со строкой аудита (`unlinked_channel_user`) и никогда не проходит онбординг: право говорить с ботом — факт компании.

## Входящее

```python
class Ingress(Protocol):
    channel: Channel
    configured: bool        # False -> the route answers 503, not 401

    def verify(self, headers: Mapping[str, str], body: bytes) -> bool:
        """True when this delivery comes from the messenger. Constant-time compare."""

    def handshake(self, body: bytes) -> str | None:
        """The plain-text answer a messenger requires before it delivers events (VK), else None."""

    def parse(self, body: bytes, *, received_at: datetime) -> InboundMessage | None:
        """A typed inbound message, or None when this update is not ours to handle."""
```

```python
@dataclass(frozen=True, slots=True)
class InboundMessage:
    dedupe_key: str          # already namespaced: "telegram:12345"
    address: Address
    sender: str              # the messenger's user id, as a string
    event: Event
    starts_run: bool         # a first contact button, not a reply
```

Правила:

1. `parse` чист и никогда не падает на неизвестном поле. Отсутствующее поле деградирует в `None`; неизвестный тип update возвращает `None`. Мессенджеры добавляют поля без предупреждения.
2. `dedupe_key` — `f"{channel}:{external_event_id}"`. Это первичный ключ `events`, поэтому повторную доставку отбрасывает база, а не код приложения.
3. `starts_run` истинно только для события первого контакта: `bot_started` или текст, начинающийся с `/start`, в MAX, `/start` в Telegram, `message_new` с текстом `/start` в VK. Всё остальное — ответ внутри существующего прогона. Повторный старт не сбрасывает прогресс: он переигрывает текущий шаг, чтобы человек получил клавиатуру заново.
4. `parse` не трогает базу, часы и сеть.

## Исходящее

```python
class Messaging(Protocol):
    channel: Channel

    async def send(self, message: OutboundMessage) -> str: ...
    async def edit(
        self, address: Address, message_id: str, text: str, keyboard: Keyboard = ()
    ) -> None: ...
```

`OutboundMessage` несёт только доменное сообщение: `address`, `text`, `keyboard` (`tuple[tuple[Button, ...], ...]`), `reply_to`. Адаптер его рендерит; `outbox` никогда не хранит payload для провода. `channel` — единственный факт о мессенджере, который раскрывает `Messaging`: диспетчеризация маршрутизирует по нему и никогда не заглядывает в адаптер.

`Sender` — более узкий порт, который получает домен: `send` и `edit` с явным `Address`, без атрибута канала. Действия и кабинет пишут через `Sender`, поэтому модульный тест даёт им `outbox`, а не мессенджер.

Сбоев два:

| Ошибка | Смысл | Диспетчер |
|---|---|---|
| `ChannelUnavailableError` | сбой транспорта или 5xx | строка возвращается в `pending` с backoff |
| `ChannelRejectedError` | 4xx, который мессенджер повторит | строка паркуется как `failed` |

Больше диспетчер молча не ловит ничего. Неожиданное исключение — баг, и оно паркуется со своим типом в `last_error`.

## Рендеринг

`core/channels.py` применяет профиль без ввода-вывода:

- `fit_text(text, profile) -> tuple[str, ...]` режет по границам абзаца, затем предложения, так что ни одна часть не превышает `max_text_chars`. Каждая часть — отдельная строка `outbox`, по порядку.
- `fit_keyboard(keyboard, profile) -> Keyboard` падает, когда клавиатура не влезает в канал (ряды, кнопки в ряду, байты payload колбэка). Сценарий, который нельзя отрендерить на включённом канале, — ошибка старта, а не сюрприз в рантайме.

Затем адаптер:

- экранирует текст в `profile.markup` (`none` значит без экранирования и без форматирования);
- отображает `Button.id` в поле колбэка канала;
- находит изображение сценария по имени через собственный каталог ресурсов и поток загрузки (сегодня MAX; Telegram и VK отправляют текст и клавиатуры, пока сообщение не понесёт изображение);
- применяет `profile.messages_per_second` и `profile.per_chat_per_second`.

## Доставка

At-least-once, по строке: `outbox` пишется в транзакции, которая записывает намерение, аренда защищает воркера, умершего посреди отправки, а запаркованная строка видна с `last_error`.

Ожидающие строки группируются по каналу и доставляются параллельно, так что мессенджер на 2 сообщения в секунду не тормозит тот, что даёт 30. Темп держится внутри адаптера: один ограничитель на канал, не один на процесс.

## Добавление канала

1. `docs/contracts/<channel>-api.md` — факты, на которые опирается адаптер, каждый с URL источника.
2. `apps/api/channel-profiles/<channel>.yaml`, проходящий `channel-profile.schema.json`.
3. Файлы `apps/api/onboarding/app/channels/<channel>/{client,ingress,render}.py`.
4. Блок настроек и запись в `CHANNELS`: токен, секрет, базовый URL. Каждый секрет — `SecretStr` и не попадает ни в один лог. `docs/runbooks/channels.md` — как оператор его включает.
5. Записи в корне композиции: `Ingress` в `ingress`, `Messaging` в `senders`.
6. Контрактные тесты: `tests/test_channel_contract.py` покрывает адаптер по параметру; фикстуры payload лежат в `tests/fixtures/channels/<channel>/` и сняты, а не придуманы.
7. Строка в `docs/README.md` и канал в «Building blocks» файла `docs/architecture.md`.

Больше ничего не меняется. `core/`, промпты, поиск, оценки и кабинет нейтральны к каналу.
