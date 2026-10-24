#!/usr/bin/env python
"""CLI над PyMax для проверки юзербот-сценариев на сессии из ~/.pymax/user.db.

Запускать интерпретатором из ~/.pymax/venv:
    ~/.pymax/venv/bin/python .pi/skills/pymax-user/scripts/pymaxctl.py me

Команды:
    me                          профиль аккаунта, под которым сессия
    chats [--limit N]           список чатов (id, type, title)
    history CHAT_ID [--limit N] последние сообщения чата
    send CHAT_ID TEXT           отправить сообщение (необратимо!)
    sessions                    активные сессии/устройства аккаунта
    users ID [ID ...]           карточки пользователей
    listen [--seconds N]        слушать события: on_start, on_message
    raw METHOD [KW=JSON ...]    произвольный вызов метода клиента

Переменные окружения:
    PYMAX_HOME      каталог с сессией и venv, по умолчанию ~/.pymax
    PYMAX_SESSION   имя файла сессии, по умолчанию user.db
    PYMAX_PHONE     телефон для регистрации новой сессии (нужен только при первом SMS-входе)

Код возврата != 0 — операция не удалась, текст ошибки в stderr.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import pathlib
import sys
from collections.abc import Awaitable, Callable
from typing import Any

try:
    from pymax import Client, Message
except ImportError:
    sys.stderr.write(
        "pymax не установлен в этом интерпретаторе.\n"
        "Запускай через ~/.pymax/venv/bin/python или подними окружение:\n"
        "  uv venv ~/.pymax/venv -p 3.13 && "
        "uv pip install --python ~/.pymax/venv/bin/python -U maxapi-python\n"
    )
    raise SystemExit(2) from None

HOME = pathlib.Path(os.environ.get("PYMAX_HOME", "~/.pymax")).expanduser()
SESSION = os.environ.get("PYMAX_SESSION", "user.db")
PHONE = os.environ.get("PYMAX_PHONE", "")

Handler = Callable[[Client, argparse.Namespace], Awaitable[None]]


def emit(line: str) -> None:
    """Печать в stdout: `print` запрещён линтером репозитория."""
    sys.stdout.write(line + "\n")


def build_client() -> Client:
    session_path = HOME / SESSION
    if not session_path.exists():
        message = (
            f"сессия не найдена: {session_path}\n"
            "Первый вход требует SMS-кода и пароля 2FA, см. SKILL.md -> «Первый вход»."
        )
        raise SystemExit(message)
    kwargs: dict[str, Any] = {"work_dir": str(HOME), "session_name": SESSION}
    if PHONE:
        kwargs["phone"] = PHONE
    return Client(**kwargs)


def dump(value: object) -> None:
    if hasattr(value, "model_dump_json"):
        emit(str(value.model_dump_json(indent=2)))  # type: ignore[attr-defined]
    elif isinstance(value, list | tuple):
        for item in value:
            dump(item)
    else:
        emit(json.dumps(value, ensure_ascii=False, default=str, indent=2))


def cmd_me(client: Client, _args: argparse.Namespace) -> Awaitable[None]:
    async def run() -> None:
        dump(client.me)

    return run()


def cmd_chats(client: Client, args: argparse.Namespace) -> Awaitable[None]:
    async def run() -> None:
        chats = await client.fetch_chats()
        for chat in chats[: args.limit]:
            emit(f"{chat.id}\t{chat.type}\t{chat.title}")

    return run()


def cmd_history(client: Client, args: argparse.Namespace) -> Awaitable[None]:
    async def run() -> None:
        # backward=N — последние N сообщений; второй позиционный аргумент это forward.
        # interactive=True обязателен: иначе сервер отбивает
        # "Chat history noninteractive limit reached".
        messages = await client.fetch_history(args.chat_id, backward=args.limit, interactive=True)
        for message in messages:
            emit(f"{message.id}\t{message.time}\t{message.text}")

    return run()


def cmd_send(client: Client, args: argparse.Namespace) -> Awaitable[None]:
    async def run() -> None:
        await client.send_message(args.chat_id, args.text)
        emit("sent")

    return run()


def cmd_sessions(client: Client, _args: argparse.Namespace) -> Awaitable[None]:
    async def run() -> None:
        dump(await client.get_sessions())

    return run()


def cmd_users(client: Client, args: argparse.Namespace) -> Awaitable[None]:
    async def run() -> None:
        dump(await client.get_users([int(item) for item in args.ids]))

    return run()


def cmd_raw(client: Client, args: argparse.Namespace) -> Awaitable[None]:
    async def run() -> None:
        kwargs = {key: json.loads(raw) for key, raw in (p.split("=", 1) for p in args.pairs)}
        dump(await getattr(client, args.method)(**kwargs))

    return run()


def cmd_listen(client: Client, args: argparse.Namespace) -> Awaitable[None]:
    async def run() -> None:
        @client.on_start()
        async def _on_start(inner: Client) -> None:
            emit(f"started profile={inner.me.contact.id}")

        @client.on_message()
        async def _on_message(message: Message, _inner: Client) -> None:
            emit(
                json.dumps(
                    {
                        "chat_id": message.chat_id,
                        "sender": str(message.sender),
                        "text": message.text,
                        "id": message.id,
                    },
                    ensure_ascii=False,
                    default=str,
                )
            )

        task = asyncio.create_task(client.start())  # start() — блокирующий listen-цикл
        try:
            await asyncio.sleep(args.seconds)
        finally:
            task.cancel()
            await client.close()

    return run()


COMMANDS: dict[str, Handler] = {
    "me": cmd_me,
    "chats": cmd_chats,
    "history": cmd_history,
    "send": cmd_send,
    "sessions": cmd_sessions,
    "users": cmd_users,
    "listen": cmd_listen,
    "raw": cmd_raw,
}
# Команды, которым нужен рабочий коннект; listen поднимает его сам через start().
CONNECTED = {"me", "chats", "history", "send", "sessions", "users", "raw"}


async def run(args: argparse.Namespace) -> None:
    client = build_client()
    handler = COMMANDS[args.command]
    if args.command not in CONNECTED:
        await handler(client, args)
        return
    await client.connect()  # one-shot: вернулся после on_start, соединение живо
    try:
        await handler(client, args)
    finally:
        await client.close()


def add_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    sub.add_parser("me", help="профиль аккаунта")
    chats = sub.add_parser("chats", help="список чатов")
    chats.add_argument("--limit", type=int, default=30)
    history = sub.add_parser("history", help="история чата")
    history.add_argument("chat_id", type=int)
    history.add_argument("--limit", type=int, default=20)
    send = sub.add_parser("send", help="отправить сообщение")
    send.add_argument("chat_id", type=int)
    send.add_argument("text")
    sub.add_parser("sessions", help="активные сессии аккаунта")
    users = sub.add_parser("users", help="карточки пользователей")
    users.add_argument("ids", nargs="+")
    listen = sub.add_parser("listen", help="слушать события")
    listen.add_argument("--seconds", type=float, default=30.0)
    raw = sub.add_parser("raw", help="произвольный метод клиента")
    raw.add_argument("method")
    raw.add_argument("pairs", nargs="*", help='KW=JSON, например text="hi"')


def main() -> int:
    parser = argparse.ArgumentParser(description="PyMax CLI поверх сохранённой сессии")
    parser.add_argument("--verbose", action="store_true", help="логи pymax в stderr")
    add_commands(parser.add_subparsers(dest="command", required=True))

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s %(message)s",
    )
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
