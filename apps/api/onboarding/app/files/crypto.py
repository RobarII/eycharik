"""Envelope encryption for documents people send in a chat.

A passport scan is the most sensitive row this service ever holds. The deployment key lives in the
environment, not in the database, so a dump alone does not reveal a document; a stolen key alone
does not either, because the ciphertext stays in Postgres.

The blob carries its own version byte: a future key rotation can re-encrypt row by row instead of
guessing how old bytes were produced.
"""

from __future__ import annotations

import base64
import binascii
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

VERSION = b"\x01"
NONCE_BYTES = 12
KEY_BYTES = 32


class EncryptionError(ValueError):
    """The key or the blob cannot be used. The message never contains key material."""


def load_key(raw: str) -> bytes | None:
    """The AES-256 key from a base64 env value, or ``None`` when no key is configured."""
    value = raw.strip()
    if not value:
        return None
    try:
        key = base64.urlsafe_b64decode(value)
    except (binascii.Error, ValueError) as error:
        raise EncryptionError("INBOUND_FILES_KEY is not valid base64") from error
    if len(key) != KEY_BYTES:
        raise EncryptionError("INBOUND_FILES_KEY must decode to 32 bytes")
    return key


def encrypt(key: bytes, data: bytes) -> bytes:
    nonce = os.urandom(NONCE_BYTES)
    return VERSION + nonce + AESGCM(key).encrypt(nonce, data, VERSION)


def decrypt(key: bytes, blob: bytes) -> bytes:
    if not blob or blob[:1] != VERSION:
        raise EncryptionError("unknown ciphertext version")
    nonce = blob[1 : 1 + NONCE_BYTES]
    try:
        return AESGCM(key).decrypt(nonce, blob[1 + NONCE_BYTES :], VERSION)
    except InvalidTag as error:
        raise EncryptionError("ciphertext does not decrypt with this key") from error
