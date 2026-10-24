---
name: pymax-user
description: "Работа с аккаунтом MAX через PyMax — неофициальный userbot API. Use when you need to read or act as a real MAX user account — listing chats, reading history, listening for events, sending messages to a chat by id, checking active sessions/devices — using the saved session in ~/.pymax. NOT for the product bot: apps/api uses the official MAX bot API (docs/contracts/max-api.md)."
---

# PyMax: юзербот от лица живого аккаунта MAX

PyMax (`maxapi-python`) — асинхронный Python-клиент **внутреннего** API мессенджера MAX.
Логинится в реальный аккаунт, видит и делает всё, что пользователь: чаты, история,
реакции, папки, контакты, активные устройства, 2FA. Бот-токена нет, официального bot API нет.

Это **не** способ писать продуктового бота. Продукт (`apps/api/`) ходит в официальный
bot API MAX через вебхук — см. `docs/contracts/max-api.md`. PyMax нужен, когда требуется
именно пользовательская точка зрения: посмотреть, что видит сотрудник в чате, найти
чат/канал по id, отправить тестовое сообщение от живого человека.

## Жёсткие правила

1. **Аккаунт один и он боевой.** Действия уходят в реальный MAX, необратимо.
   `send_message` от лица человека увидят живые люди. Перед отправкой — спросить пользователя.
2. **Сессия = ключ от аккаунта.** `~/.pymax/user.db` содержит токен. Никогда в git,
   в вывод, в отчёт, в коммит, в другой каталог репозитория. `.pymax` живёт вне
   `~/eycharik` именно поэтому.
3. **Секретов в переписке и файлах скилла нет.** Ни телефона, ни SMS-кода, ни пароля 2FA,
   ни токена. Телефон берётся из `PYMAX_PHONE`, только если сессии нет.
4. **Неофициальный API.** Может смениться без предупреждения; авторы предупреждают про
   нарушение ToS и риск блокировки аккаунта. Ошибку API цитировать дословно, не выдумывать
   обходной путь наугад.

## Окружение (уже поднято)

| Что | Где |
|---|---|
| venv с `pymax==2.4.1` | `~/.pymax/venv` |
| сессия пользователя | `~/.pymax/user.db` (chmod 600, каталог 700) |
| CLI-хелпер | `.pi/skills/pymax-user/scripts/pymaxctl.py` |

Запускать только интерпретатором оттуда, иначе `import pymax` упадёт:

```bash
export PYMAX_PHONE=+79XXXXXXXXX        # нужен лишь при создании новой сессии
~/.pymax/venv/bin/python .pi/skills/pymax-user/scripts/pymaxctl.py me
```

Каталог/имя сессии переопределяются: `PYMAX_HOME` (по умолчанию `~/.pymax`),
`PYMAX_SESSION` (по умолчанию `user.db`).

## CLI-хелпер: что умеет

```bash
P=~/.pymax/venv/bin/python
S=.pi/skills/pymax-user/scripts/pymaxctl.py

$P $S me                                     # профиль: id, имя, телефон, опции
$P $S chats --limit 30                       # id \t type \t title
$P $S history CHAT_ID --limit 20             # id \t time \t text
$P $S send CHAT_ID "текст"                   # ИЗМЕНЯЕТ РЕАЛЬНЫЙ ЧАТ, спросить до
$P $S sessions                               # активные устройства аккаунта
$P $S users 502781191 123456                 # карточки пользователей
$P $S listen --seconds 30                    # flow: on_start + on_message в stdout
$P $S raw get_chat chat_id=278874685         # произвольный метод, аргументы в JSON
$P $S --verbose me                           # логи pymax в stderr
```

Код возврата `!= 0` — операция не удалась, реальная ошибка в stderr. Не глотать traceback:
`ApiError` содержит текст сервера, он и есть диагноз.

## Свой скрипт вместо CLI

```python
import asyncio
from pymax import Client

async def main() -> None:
    c = Client(phone="+79XXXXXXXXX", work_dir="/Users/yegor/.pymax", session_name="user.db")
    await c.connect()          # one-shot: вернулся после on_start, соединение живо
    try:
        print(c.me.contact.id, c.me.contact.names[0].first_name)
        for chat in await c.fetch_chats():
            print(chat.id, chat.type, chat.title)
        msgs = await c.fetch_history(CHAT_ID, backward=20, interactive=True)
        for m in msgs:
            print(m.id, m.time, m.text)
    finally:
        await c.close()

asyncio.run(main())
```

### Грабли, на которые уже наступали

- **`start()` — это listen-цикл.** Внутри `while True` + `wait_closed()` + reconnect,
  он не возвращает управление. Для разовых действий — `connect()`, для событий —
  `start()` в `create_task` и потом `task.cancel()` + `close()`.
- **`fetch_history` без `interactive=True`** отбивается сервером:
  `ApiError: Слишком много запросов Chat history noninteractive limit reached`.
- **`fetch_history(chat_id, N)`** — второй позиционный аргумент это `forward`,
  а не «сколько». Последние N сообщений: `backward=N`.
- **TLS.** `api2.oneme.ru` подписан «Russian Trusted Sub CA» (Минцифры), его нет ни в
  certifi, ни в macOS keychain. PyMax сам грузит `pymax/_data/rootca_ssl_rsa2022.crt`,
  поэтому ничего докидывать не надо. Ручной `ssl.create_default_context()` в своём коде
  даст `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate` — это не сеть.
- **Сеть напрямую.** `api2.oneme.ru:443`, `api.oneme.ru:443`, `hashes.pymax.org:443`
  доступны без SOCKS-туннеля. Туннель из `AGENTS.md` нужен провайдерам моделей, не MAX.
  Если нужен прокси — `ExtraConfig(proxy="socks5://...")`.
- **`client.me` до `connect()`** — `None`. Проверять после старта.
- **`message.answer(...)`, `message.reply(...)`** работают на объекте сообщения;
  `send_message(chat_id, text)` — на клиенте.

## Первый вход (сессии нет)

Нужны телефон владельца аккаунта, SMS-код и пароль 2FA. Без них никак: QR-путь
(`WebClient` + `QrAuthFlow`) требует, чтобы владелец отсканировал QR в приложении MAX.

```python
from pymax import Client, SmsAuthFlow, SmsCodeProvider, ConsolePasswordProvider
import asyncio

class MyCode(SmsCodeProvider):
    async def get_code(self, *a, **k) -> str:
        return input("SMS код: ").strip()          # в агентской сессии — из файла/env, не из чата

async def main() -> None:
    c = Client(phone="+79XXXXXXXXX", work_dir="/Users/yegor/.pymax", session_name="user.db",
               auth_flow=SmsAuthFlow(code_provider=MyCode()))
    await c.start()      # интерактивный вход, потом блокирующий listen
```

Порядок диалога с пользователем: спросить телефон -> запустить вход -> на
`WAITING_FOR_SMS_CODE` попросить код -> на `WAITING_FOR_PASSWORD` попросить пароль 2FA ->
дождаться `client started profile=<id>` и `new session saved`. Файл `user.db`
(chmod 600) и есть сохранённая сессия; повторный запуск идёт без SMS.

## Отзыв доступа

```python
await c.logout()                # убить текущую сессию
await c.close_all_sessions()    # выкинуть все устройства
```

Либо вручную: приложение MAX -> Настройки -> Устройства. Если сессия утекла — только так.

## Дальше

Полная карта методов клиента, типы событий и модели — `references/api-map.md`.
