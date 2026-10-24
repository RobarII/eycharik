---
title: Включение канала
summary: Как включить Telegram или VK рядом с MAX и доказать, что канал работает от вебхука до доставки.
kind: прогон
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Прогон: включить канал

MAX включён по умолчанию. Telegram и VK выключены, пока окружение не скажет иначе: канал без
секрета и привязанного аккаунта — открытая дверь (ADR 0019). Этот ранбук включает канал и
доказывает, что он работает.

## Условия

- `make check` зелёный, миграции применены: `channel_identities` есть, у каждого сотрудника есть
  привязка к MAX.
- `apps/api/channel-profiles/<channel>.yaml` проходит проверку по
  `docs/contracts/channel-profile.schema.json`. `make check` это покрывает.
- Есть токен бота и секрет вебхука мессенджера, и публичное имя хоста из `docs/runbooks/deploy.md`.

## Шаги

1. Задайте окружение и перезапустите оба процесса:

```bash
CHANNELS=max,telegram        # the enabled set; an unknown name fails at startup
TELEGRAM_BOT_TOKEN=...       # never in git
TELEGRAM_WEBHOOK_SECRET=...  # the value Telegram echoes in X-Telegram-Bot-Api-Secret-Token
```

   Для VK: `CHANNELS=max,vk`, `VK_ACCESS_TOKEN`, `VK_WEBHOOK_SECRET`, `VK_CONFIRMATION_CODE`. VK
   нужны все три.

   Канал в `CHANNELS` без секрета вебхука (а для VK — без кода подтверждения) не регистрируется
   вообще: его роут отвечает `404`, поэтому незавершённая настройка не примет доставки. `503` от
   зарегистрированного роута значит, что процесс потерял секрет на ходу, — проверяйте окружение,
   не мессенджер.

2. Привяжите тестовый аккаунт к сотруднику. Больше ничего постороннего не пускает:

```bash
curl -X POST https://$HOST/admin/api/identities \
  -H "Authorization: Bearer $HR_TOKEN" -H "content-type: application/json" \
  -d '{"channel": "telegram", "external_id": "222", "employee_id": "1001"}'
```

   `external_id` — собственный id пользователя в мессенджере: `from.id` в Telegram, `from_id`/
   `user_id` в VK. Это не id чата и не id сотрудника.

3. Зарегистрируйте вебхук.

   Telegram: CLI вызывает `setWebhook` с токеном и секретом из окружения.

```bash
uv run python -m onboarding.cli webhook --channel telegram --url "https://$HOST/webhook/telegram"
```

   VK: в настройках сообщества добавьте сервер Callback API с URL `https://$HOST/webhook/vk`,
   вставьте секрет и включите типы `message_new` и `message_event`. VK показывает строку
   подтверждения на вкладке сервера; она должна совпадать с `VK_CONFIRMATION_CODE`. VK вызывает URL
   с `{"type": "confirmation"}` и ждёт эту строку обратно простым текстом, без перевода строки в
   конце, в течение пяти секунд. Роут отвечает на рукопожатие до проверки секрета, потому что VK
   сначала доказывает адрес, а потом уж отправляет.

   Страница настроек VK — самое ненадёжное место во всём этом. Она показывает заглушку в поле
   секрета, даже когда секрет сохранён, поэтому одно поле ничего не доказывает, а скриптовая
   вставка не всегда доходит до модели VK: секрет остаётся пустым, и каждое событие получает
   `401`. Спрашивайте API, а не страницу:

```bash
# the address is confirmed when status is ok; secret_key must equal VK_WEBHOOK_SECRET
curl -s https://api.vk.com/method/groups.getCallbackServers \
  -d group_id=$VK_GROUP_ID -d v=5.199 -d access_token=$VK_ACCESS_TOKEN

# set or repair the secret; returns the server id
curl -s https://api.vk.com/method/groups.editCallbackServer \
  -d group_id=$VK_GROUP_ID -d server_id=$VK_SERVER_ID -d v=5.199 \
  --data-urlencode url=https://$HOST/webhook/vk \
  --data-urlencode secret_key=$VK_WEBHOOK_SECRET \
  -d access_token=$VK_ACCESS_TOKEN

# enabled types: message_new and message_event must be true
curl -s https://api.vk.com/method/groups.getCallbackSettings \
  -d group_id=$VK_GROUP_ID -d server_id=$VK_SERVER_ID -d v=5.199 \
  -d access_token=$VK_ACCESS_TOKEN
```

   VK меняет строку подтверждения без предупреждения и держит старую на странице, пока та не
   перерисуется, поэтому если «Подтвердить» продолжает падать, перечитайте строку со свежей
   страницы и сверьте с `VK_CONFIRMATION_CODE`, прежде чем менять что-то ещё. `200` в логе API
   рядом с падающей страницей — не доказательство ни в одну сторону: VK фиксирует запрос, а решает
   `getCallbackServers`.

4. Отправьте `/start` с привязанного аккаунта. Ожидается: строка `events` с ключом `<channel>:<id>`,
   строка `jobs`, которая доходит до `done`, сообщение в очереди, у которого колонка `channel` —
   новый канал, и одно приветственное сообщение в мессенджере.

5. Отправьте `/start` с непривязанного аккаунта. Ожидается `200`, без прогона, без сообщения и одна
   строка аудита:

```sql
select name, fields from audit_log where name = 'unlinked_channel_user' order by id desc limit 5;
```

## Как доказать канал целиком

`scripts/channel_smoke.py` шлёт апдейты в форме мессенджера на публичный вебхук, а потом читает
базу, поэтому зелёный прогон значит, что работает весь путь: проверка, идентичность, дедупликация,
сценарий, `outbox`, адаптер и собственный id сообщения мессенджера.

```bash
MAX_WEBHOOK_SECRET=... DATABASE_URL=... \
  uv run python scripts/channel_smoke.py --channel max \
    --base-url https://$HOST --chat-id $CHAT_ID --reset

TELEGRAM_WEBHOOK_SECRET=... DATABASE_URL=... \
  uv run python scripts/channel_smoke.py \
    --base-url https://$HOST --chat-id $CHAT_ID --reset

VK_WEBHOOK_SECRET=... VK_GROUP_ID=... DATABASE_URL=... \
  uv run python scripts/channel_smoke.py --channel vk \
    --base-url https://$HOST --chat-id $PEER_ID --reset
```

Для VK `--chat-id` — это `peer_id` из строки аудита сообщения, которое аккаунт отправил первым:
сообщество не может начать переписку, так что отправлять некуда, пока человек не напишет.

Смоук MAX шлёт `bot_started`, `message_created` и `message_callback` с заголовком
`X-Max-Bot-Api-Secret`, поэтому годится и публичный хост, и локальный прогон: `MAX_BASE_URL`
указывает адаптеру, куда отправлять, так что фейковый сервер на `127.0.0.1` заменяет платформу
целиком — вебхук, сценарий, `outbox` и id сообщения проверяются без токена и без сети MAX.

Тот же путь без публичного хоста и без токена проверяет интеграционный тест:

```bash
ONBOARDING_TEST_DATABASE=postgresql+asyncpg://... uv run pytest \
  apps/api/tests/test_max_e2e.py -m integration
```

Он шлёт апдейты на настоящее приложение, гоняет воркер и диспетчер и сверяет тело
`POST /messages` с контрактом: заголовок, `chat_id`, текст, вложения, кнопки, токен медиа. Ответ
платформы подменён строгим фейком, а не «любой JSON».

MAX доставляет входящие файлы: `parse_update` разбирает `message.body.attachments`, воркер
скачивает байты только с хоста MAX, шифрует AES-GCM и кладёт в `inbound_files` ([ADR 0027](../decisions/0027-inbound-documents-are-encrypted.md)).
Смоук проходит шаг, который ждёт документ; что байты легли зашифрованными, проверяют
интеграционные тесты и карточка кабинета. Исходящие изображения идут отдельной двухшаговой загрузкой.

Скрипт проходит сценарий целиком, жмёт первую опцию на каждой клавиатуре, прикладывает документ
там, где шаг ждёт файл, и затем проверяет доставку, лимит текста, отказы (нет секрета, неверный
секрет, не-JSON, тело сверх лимита, выключенный канал), правило непривязанного аккаунта и повторную
доставку. `--branch trouble` жмёт вместо этого последнюю опцию, что прогоняет несчастливые ветки и
подсчёт риска. `--scenario` выбирает сценарий для прогона.

Отказы следуют за каналом: MAX и Telegram несут секрет в заголовке, поэтому тело не-JSON доходит
до парсера и получает `400`; VK несёт секрет в теле, поэтому неразбираемое тело проверить нельзя
вообще и оно получает `401`.

### Как доказать, что прогон следует за человеком

Один сценарий, два мессенджера. `--switch-to` ведёт чат того же сотрудника во втором канале, так
что смоук доказывает обещанное ADR 0019, а не предполагает:

```bash
TELEGRAM_WEBHOOK_SECRET=... VK_WEBHOOK_SECRET=... VK_GROUP_ID=... DATABASE_URL=... \
  uv run python scripts/channel_smoke.py --channel vk \
    --base-url https://$HOST --chat-id $PEER_ID --group-id $GROUP_ID \
    --switch-to telegram --switch-chat-id $TELEGRAM_CHAT_ID --reset
```

Оба чата уже привязаны к одному сотруднику (`/admin/api/identities`), и смоук пишет в оба.
Добавленные проверки: старт в другом мессенджере переносит прогон туда и заново задаёт текущий
вопрос в новой переписке; id прогона, его шаг и индекс вопроса не меняются; ответ, набранный в
новом мессенджере, двигает тот же прогон; старт обратно в первом мессенджере возвращает адрес; и
каждый перенос оставляет строку аудита `channel_changed`. Затем доставка, лимит текста и отказы
проверяются в обоих каналах.

Прогону нужен привязанный чат: аккаунт мессенджера скрипт не выдумает, а непривязанный отклоняется
по замыслу. Telegram спрашивают напрямую, поэтому `api.telegram.org` должен быть доступен с хоста,
где идёт смоук (используйте `HTTPS_PROXY`, когда нет). Воркеру нужен тот же прокси: с устаревшим
сценарий всё равно двигается — прогон не зависит от доставки, — но каждая исходящая строка остаётся
в `pending` с `last_error` = `ConnectError`, и смоук сообщает `0/N sent`.

## Проверочные запросы

```sql
select channel, count(*) from messages group by channel;
select channel, count(*) from runs group by channel;
select channel, count(*) from channel_identities group by channel;
select fields->>'channel' as to_channel, count(*) from audit_log
  where name = 'channel_changed' group by 1;
```

Сообщение, застрявшее в `pending` в одном канале, пока остальные доставляются, значит токен или
лимит этого канала, а не диспетчер: диспетчер арендует строки по каналам, и один падающий канал не
блокирует остальные.

## Откат

Уберите канал из `CHANNELS` и перезапустите. Его входящий роут отвечает `404`, строки в очереди
остаются в `messages` нетронутыми, ничего не удаляется. Строки этого канала продолжатся, когда его
включат снова.
