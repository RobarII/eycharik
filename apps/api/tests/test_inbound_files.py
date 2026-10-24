from __future__ import annotations

import base64

import pytest

from onboarding.app.files.crypto import EncryptionError, decrypt, encrypt, load_key
from onboarding.app.files.intake import safe_filename, sniff_media_type

JPEG = b"\xff\xd8\xff\xe0" + b"x" * 20
PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 20
PDF = b"%PDF-1.7\n" + b"x" * 20
WEBP = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"x" * 20
HEIC = b"\x00\x00\x00\x18ftypheic" + b"x" * 20
KEY = bytes(range(32))


def test_the_sniffer_reads_bytes_not_names() -> None:
    assert sniff_media_type(JPEG) == "image/jpeg"
    assert sniff_media_type(PNG) == "image/png"
    assert sniff_media_type(PDF) == "application/pdf"
    assert sniff_media_type(WEBP) == "image/webp"
    assert sniff_media_type(HEIC) == "image/heic"
    assert sniff_media_type(b"<html>") is None
    assert sniff_media_type(b"") is None


def test_a_bare_filename_gets_an_extension_from_its_type() -> None:
    assert safe_filename(None, "image/jpeg", "abc") == "file-abc.jpg"
    assert safe_filename("", "application/pdf", "abcdefgh") == "file-abcdefgh.pdf"


def test_a_path_in_a_filename_cannot_escape_the_download_directory() -> None:
    assert safe_filename("../../etc/passwd", "image/jpeg", "t") == "passwd"
    assert safe_filename("C:\\Users\\hr\\паспорт.pdf", "application/pdf", "t") == "паспорт.pdf"
    assert safe_filename("..\\..\\x.jpg", "image/jpeg", "t") == "x.jpg"


def test_control_characters_are_replaced_and_the_length_is_capped() -> None:
    assert safe_filename("паспорт\nновый.jpg", "image/jpeg", "t") == "паспорт_новый.jpg"
    long_name = "a" * 400 + ".jpg"
    assert len(safe_filename(long_name, "image/jpeg", "t")) <= 120


def test_encryption_round_trips_and_never_stores_plaintext() -> None:
    blob = encrypt(KEY, JPEG)

    assert JPEG not in blob
    assert decrypt(KEY, blob) == JPEG
    assert encrypt(KEY, JPEG) != blob  # a fresh nonce per write


def test_the_wrong_key_fails_loudly() -> None:
    blob = encrypt(KEY, JPEG)

    with pytest.raises(EncryptionError):
        decrypt(bytes(reversed(KEY)), blob)


def test_a_key_must_be_base64_of_32_bytes() -> None:
    assert load_key("") is None
    assert load_key(base64.urlsafe_b64encode(KEY).decode()) == KEY
    with pytest.raises(EncryptionError, match="base64"):
        load_key("not base64!")
    with pytest.raises(EncryptionError, match="32 bytes"):
        load_key(base64.urlsafe_b64encode(b"short").decode())


def test_a_blob_from_a_future_version_is_refused() -> None:
    with pytest.raises(EncryptionError, match="version"):
        decrypt(KEY, b"\x02" + b"x" * 30)
