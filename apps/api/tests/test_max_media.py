from __future__ import annotations

from pathlib import Path

import pytest

from onboarding.app.channels.max.media import (
    ImageAssetError,
    asset_path,
    image_attachment,
    upload_token,
)


def test_resolves_a_bundled_image(tmp_path: Path) -> None:
    (tmp_path / "welcome.jpg").write_bytes(b"jpeg")

    assert asset_path(tmp_path, "welcome.jpg") == (tmp_path / "welcome.jpg").resolve()


@pytest.mark.parametrize("name", ["../welcome.jpg", "a/welcome.jpg", "welcome.gif"])
def test_rejects_names_outside_the_bundle(tmp_path: Path, name: str) -> None:
    with pytest.raises(ImageAssetError):
        asset_path(tmp_path, name)


def test_rejects_a_missing_image(tmp_path: Path) -> None:
    with pytest.raises(ImageAssetError, match="missing"):
        asset_path(tmp_path, "ghost.jpg")


def test_builds_the_documented_attachment_shape() -> None:
    assert image_attachment("token-1") == {"type": "image", "payload": {"token": "token-1"}}


def test_reads_both_documented_upload_responses() -> None:
    assert upload_token({"token": "top"}) == "top"
    assert upload_token({"photos": {"photoIds": {"token": "nested"}}}) == "nested"
    assert upload_token({"photos": {"photos": [{"token": "list"}]}}) == "list"
    assert upload_token({}) is None
