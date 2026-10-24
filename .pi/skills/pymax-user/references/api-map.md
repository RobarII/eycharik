---
title: Карта API PyMax 2.4.1
summary: Методы клиента, события, модели и транспорт PyMax 2.4.1 — шпаргалка к скиллу pymax-user.
kind: reference
owner: agent
status: actual
last_verified: 2026-10-24
---

# Карта API PyMax 2.4.1

Снято интроспекцией пакета `maxapi-python==2.4.1` (Python 3.13, venv `~/.pymax/venv`).
Подписи сокращены: `pymax.types.domain.message.Message` -> `Message`.

## Клиент

```python
from pymax import Client, WebClient, ExtraConfig
Client(phone: str, session_name="session.db", work_dir=".", extra_config=None,
       auth_flow=None, sms_code_provider=None, password_provider=None,
       app_version="26.25.0", catalog=None)
WebClient(session_name="session.db", work_dir=".", extra_config=None,
          auth_flow=None, qr_provider=None)
```

`ExtraConfig`: `token`, `proxy`, `host` (по умолчанию `api2.oneme.ru`), `port` (443),
`use_ssl`, `url` (`wss://api.oneme.ru/websocket`), `reconnect`, `request_timeout`,
`telemetry`, `store`, `sync`, `registration_config`.

`start()` — listen-цикл до закрытия соединения (reconnect, relogin). `connect()` — один раз,
возвращается после `on_start`, соединение остаётся. `stop()`/`close()` — закрыть.

### Аккаунт, сессия, профиль

- `me` (свойство)
- `contacts` (свойство)
- `chats` (свойство)
- `messages` (свойство)
- `get_sessions() -> list[Session]`
- `close_all_sessions() -> bool`
- `logout() -> bool`
- `close() -> 'None'`
- `connect(: 'ClientT') -> 'None'`
- `start(: 'ClientT') -> 'None'`
- `stop() -> 'None'`
- `relogin(: 'ClientT', drop_config_token: 'bool' = True, start: 'bool' = True) -> 'None'`
- `is_connected` (свойство)
- `check_2fa() -> bool`
- `set_2fa(password: str, email: str | MissingType = MISSING, hint: str | MissingType = MISSING, email_code_provider: EmailCodeProvider | None = None) -> bool`
- `remove_2fa(password: str) -> bool`
- `change_password(password_old: str, password_new: str) -> bool`
- `change_profile(first_name: str, last_name: str | None = None, description: str | None = None, photo: Photo | None = None, *, photo_token: str | None = None) -> bool`
- `change_profile_settings(settings: PrivacySettingsUpdate) -> bool`
- `is_update_available() -> bool`
- `search_by_phone(phone: str) -> User`
- `get_cached_user(user_id: int) -> User | None`
- `get_user(user_id: int) -> User | None`
- `get_users(user_ids: list[int]) -> list[User]`
- `fetch_users(user_ids: list[int]) -> list[User]`
- `add_contact(contact_id: int) -> User`
- `remove_contact(contact_id: int) -> Literal[True]`
- `import_contacts(contacts: list[ContactInfo]) -> list[User]`
- `set_presence(*, online: bool) -> None`

### Чаты и сообщения

- `fetch_chats(marker: int | None = None) -> list[Chat]`
- `get_chats(chat_ids: list[int]) -> list[Chat]`
- `get_chat(chat_id: int) -> Chat`
- `get_chat_id(first_user_id: int, second_user_id: int) -> int`
- `fetch_history(chat_id: int, forward: int = 0, backward: int = 40, backward_time: int = 0, forward_time: int = 0, from_time: int | None = None, item_type: ItemType = <ItemType.REGULAR: 'REGULAR'>, get_chat: bool = False, get_messages: bool = True, interactive: bool = False) -> list[Message]`
- `get_message(chat_id: int, message_id: int) -> Message | None`
- `get_messages(chat_id: int, message_ids: list[int]) -> list[Message]`
- `send_message(chat_id: int, text: str | None = None, reply_to: int | None = None, attachments: Sequence[Attachment] | None = None, *, notify: bool = True, send_at: datetime.datetime | datetime.timedelta | int | None = None) -> Message`
- `edit_message(chat_id: int, message_id: int, text: str | None = None, attachments: Sequence[Attachment] | None = None) -> Message`
- `delete_message(chat_id: int, message_ids: list[int], for_me: bool) -> bool`
- `forward_message(chat_id: int, message_id: int | str, source_chat_id: int | None = None, *, notify: bool = True) -> Message`
- `read_message(message_id: int | str, chat_id: int) -> ReadState`
- `pin_message(chat_id: int, message_id: int, notify_pin: bool) -> bool`
- `add_reaction(chat_id: int, message_id: int, reaction: str) -> ReactionInfo | None`
- `remove_reaction(chat_id: int, message_id: int) -> ReactionInfo | None`
- `get_reactions(chat_id: int, message_ids: list[int]) -> dict[str, ReactionInfo] | None`
- `vote_poll(chat_id: int, message_id: int, poll_id: int, answer_ids: list[int]) -> PollState`
- `get_chat_members(chat_id: int, marker: int | None = None, count: int = 50) -> tuple[list[Member], int]`

### Группы и каналы

- `create_group(name: str, participant_ids: list[int] | None = None, notify: bool = True) -> tuple[Chat, Message] | None`
- `change_group_profile(chat_id: int, name: str | None = None, description: str | None = None, photo: Photo | None = None) -> None`
- `change_group_settings(chat_id: int, all_can_pin_message: bool | None = None, only_owner_can_change_icon_title: bool | None = None, only_admin_can_add_member: bool | None = None, only_admin_can_call: bool | None = None, members_can_see_private_link: bool | None = None) -> None`
- `invite_users_to_group(chat_id: int, user_ids: list[int], show_history: bool = True) -> Chat | None`
- `invite_users_to_channel(chat_id: int, user_ids: list[int], show_history: bool = True) -> Chat | None`
- `remove_users_from_group(chat_id: int, user_ids: list[int], clean_msg_period: int) -> bool`
- `leave_group(chat_id: int) -> None`
- `leave_channel(chat_id: int) -> None`
- `join_group(link: str) -> Chat`
- `join_channel(link: str) -> Chat`
- `resolve_group_by_link(link: str) -> Chat | None`
- `rework_invite_link(chat_id: int) -> Chat`
- `add_admin(chat_id: int, user_id: int, permissions: list[ChannelPermissions]) -> None`
- `get_join_requests(chat_id: int, count: int = 100) -> list[Member]`
- `confirm_join_request(chat_id: int, user_id: int, show_history: bool = True) -> Chat | None`
- `confirm_join_requests(chat_id: int, user_ids: list[int], show_history: bool = True) -> Chat | None`
- `decline_join_request(chat_id: int, user_id: int) -> Chat | None`
- `decline_join_requests(chat_id: int, user_ids: list[int]) -> Chat | None`
- `delete_chat(chat_id: int, last_event_time: int | None = None, for_all: bool = True) -> None`

### Папки

- `get_folders(folder_sync: int = 0) -> FolderList`
- `create_folder(title: str, chat_include: list[int], filters: list[typing.Any] | None = None) -> FolderUpdate`
- `update_folder(folder_id: str, title: str, chat_include: list[int] | None = None, filters: list[typing.Any] | None = None, options: list[typing.Any] | None = None) -> FolderUpdate`
- `delete_folder(folder_id: str) -> FolderUpdate`

### Файлы

- `get_file_by_id(chat_id: int, message_id: int | str, file_id: int) -> FileRequest | None`
- `get_video_by_id(chat_id: int, message_id: int | str, video_id: int) -> VideoRequest | None`
- `request_profile_photo_upload_url() -> str`

### События (декораторы)

- `on_start() -> 'StartDecorator[ClientT]'`
- `on_message(*filters: 'FilterCallback[Message]') -> 'HandlerDecorator[Message, ClientT]'`
- `on_message_edit(*filters: 'FilterCallback[Message]') -> 'HandlerDecorator[Message, ClientT]'`
- `on_message_delete(*filters: 'FilterCallback[MessageDeleteEvent]') -> 'HandlerDecorator[MessageDeleteEvent, ClientT]'`
- `on_message_read(*filters: 'FilterCallback[MessageReadEvent]') -> 'HandlerDecorator[MessageReadEvent, ClientT]'`
- `on_typing(*filters: 'FilterCallback[TypingEvent]') -> 'HandlerDecorator[TypingEvent, ClientT]'`
- `on_presence(*filters: 'FilterCallback[PresenceEvent]') -> 'HandlerDecorator[PresenceEvent, ClientT]'`
- `on_reaction_update(*filters: 'FilterCallback[ReactionUpdateEvent]') -> 'HandlerDecorator[ReactionUpdateEvent, ClientT]'`
- `on_chat_update(*filters: 'FilterCallback[Chat]') -> 'HandlerDecorator[Chat, ClientT]'`
- `on_raw(*filters: 'FilterCallback[InboundFrame]') -> 'HandlerDecorator[InboundFrame, ClientT]'`
- `on_error(scope: 'ErrorScope' = <ErrorScope.GLOBAL: 'global'>) -> 'ErrorDecorator[ClientT]'`
- `on_disconnect() -> 'DisconnectDecorator'`
- `include_router(router: 'Router[ClientT]') -> 'None'`

### Прочее

- `get_bot_init_data(bot_id: int, chat_id: int | None = None, start_param: str | None = None) -> InitData`
- `authorize_qr_login(qr_link: str) -> bool`
- `get_chat_id(first_user_id: int, second_user_id: int) -> int`

## События

`EventType`: `message_new`, `message_edit`, `message_delete`, `message_read`, `typing`,
`presence`, `reaction_update`, `chat_update`, `user_update`, `video_ready`, `file_ready`,
`voice_ready`, `raw`, `on_start`.

Декораторы `Client`/`Router`: `on_start`, `on_message`, `on_message_edit`,
`on_message_delete`, `on_message_read`, `on_typing`, `on_presence`, `on_reaction_update`,
`on_chat_update`, `on_raw`, `on_error`, `on_disconnect`. Обработчик получает
`(event, client)`. Группировка — `Router` + `include_router`, фильтры — `*filters`.

## Модели

- `Chat`: `id, type, status, owner, participants, title, base_raw_icon_url, base_icon_url,
  last_message, last_event_time, created, new_messages, link, access, restrictions,
  pinned_message, participants_count, description, options, join_time, invited_by,
  modified, messages_count, has_bots, prev_message_id, admin_participants, admins, cid`
- `User`: `id, account_status, registration_time, country, base_raw_url, base_url, names,
  options, photo_id, update_time, phone, status, description, gender, link, web_app, menu_button`
- `Message`: `id, chat_id, sender, text, time, type, cid, attaches, stats, status,
  reaction_info, options, prev_message_id, ttl, unread, mark, elements,
  delayed_attributes, link`. Шорткаты: `answer()`, `reply()`, `edit()`, `delete()`,
  `forward()`, `react()`, `unreact()`, `pin()`, `read()`, `get_reactions()`
- `types.domain.session.Session`: `id, device_id, current, user_agent, app_version,
  device_name, device_type, platform, ip, location, created, updated, last_activity, options`
- `Chat.type`: `DIALOG`, `CHANNEL`, `CHAT` (`GET_CHAT_ID`-диалог с собой приходит как `id=0`)

## Транспорт и TLS

- TCP `api2.oneme.ru:443`, mobile handshake, протокол msgpack + zstandard.
- WebSocket `wss://api.oneme.ru/websocket`, origin `https://web.max.ru`.
- Сертификат `*.oneme.ru` выпущен «Russian Trusted Sub CA» (Минцифры). PyMax грузит
  собственный корневой CA `pymax/_data/rootca_ssl_rsa2022.crt` в
  `pymax/transport/tcp.py`; системные хранилища (certifi, macOS keychain) его не знают,
  поэтому свой `ssl.create_default_context()` даст
  `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`.
- Каталог версий мобильного клиента и fingerprints: `https://hashes.pymax.org/versions.json`.
- Сессия: SQLite (`<work_dir>/<session_name>`), хранит login token и sync-state.

## Ошибки

`pymax.exceptions.PyMaxError` -> `ApiError` (поля `opcode`, текст сервера),
`PasswordAttemptsExceededError`, `UploadError`.
Реальные тексты, уже встречавшиеся:

- `ApiError: Слишком много запросов Chat history noninteractive limit reached` —
  `fetch_history` без `interactive=True`.
- `CERTIFICATE_VERIFY_FAILED ... unable to get local issuer certificate` — свой SSL-контекст
  вместо встроенного CA PyMax.
