"""Channel profiles: what each messenger can carry, as data.

One YAML per channel, validated against ``docs/contracts/channel-profile.schema.json`` at startup,
so a limit the channel cannot honour is a deployment error rather than a failed delivery. The same
shape as model profiles (ADR 0013) and extraction profiles (ADR 0015); ADR 0019 explains why the
channel is data and not a branch.

I/O lives here. ``onboarding.core.channels`` only ever sees a value.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from onboarding.core.channels import ChannelProfile, ChannelProfileError
from onboarding.core.models import Channel

MAX_PROFILE_BYTES = 8_000
_NAME = re.compile(r"[a-z][a-z0-9_]*")


class ChannelProfileLibrary:
    """Read one profile per configured channel and refuse an inconsistent set."""

    def __init__(self, root: Path, schema_path: Path) -> None:
        self._root = root
        self._schema_path = schema_path
        self._validator: Draft202012Validator | None = None
        self._cache: dict[Channel, ChannelProfile] = {}

    def load(self, channel: Channel) -> ChannelProfile:
        if channel not in self._cache:
            self._cache[channel] = _profile(self._read(channel), channel=channel)
        return self._cache[channel]

    def load_all(self) -> dict[Channel, ChannelProfile]:
        return {channel: self.load(channel) for channel in Channel}

    def available(self) -> tuple[str, ...]:
        if not self._root.is_dir():
            return ()
        return tuple(sorted(path.stem for path in self._root.glob("*.yaml")))

    def _read(self, channel: Channel) -> dict[str, Any]:
        name = channel.value
        if not _NAME.fullmatch(name):
            raise ChannelProfileError(f"invalid channel profile name {name!r}")
        path = self._root / f"{name}.yaml"
        if not path.is_file():
            known = ", ".join(self.available()) or "none"
            raise ChannelProfileError(
                f"missing channel profile {path} (known profiles: {known})"
            )
        if path.stat().st_size > MAX_PROFILE_BYTES:
            raise ChannelProfileError(f"{path} exceeds {MAX_PROFILE_BYTES} bytes")
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            raise ChannelProfileError(f"{path}: not valid YAML: {error}") from None
        if not isinstance(data, dict):
            raise ChannelProfileError(f"{path}: expected a mapping")
        if data.get("channel") != name:
            raise ChannelProfileError(
                f"{path}: channel is {data.get('channel')!r}, but the file is {name}.yaml"
            )
        failures = sorted(
            self._contract().iter_errors(data), key=lambda failure: list(failure.path)
        )
        if failures:
            failure = failures[0]
            where = "/".join(str(part) for part in failure.path) or "profile"
            raise ChannelProfileError(f"{path}: {where}: {failure.message}")
        return data

    def _contract(self) -> Draft202012Validator:
        if self._validator is None:
            schema = json.loads(self._schema_path.read_text(encoding="utf-8"))
            self._validator = Draft202012Validator(schema, format_checker=FormatChecker())
        return self._validator


def _profile(data: dict[str, Any], *, channel: Channel) -> ChannelProfile:
    optional = {
        "callback_payload_bytes": data.get("callback_payload_bytes"),
    }
    profile = ChannelProfile(
        channel=channel,
        max_text_chars=int(data["max_text_chars"]),
        max_keyboard_rows=int(data.get("max_keyboard_rows", 3)),
        max_buttons_per_row=int(data.get("max_buttons_per_row", 3)),
        keyboard_scope=data.get("keyboard_scope", "message"),
        supports_image=bool(data.get("supports_image", True)),
        supports_edit=bool(data.get("supports_edit", True)),
        markup=data.get("markup", "none"),
        messages_per_second=float(data["messages_per_second"]),
        per_chat_per_second=data.get("per_chat_per_second"),
        **optional,
    )
    profile.validate()
    return profile
