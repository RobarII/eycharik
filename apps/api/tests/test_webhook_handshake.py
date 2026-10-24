"""The webhook order: handshake, then the secret, then the body.

VK proves an address before it delivers anything and sends no secret with that request, so the
handshake has to be answerable by a server that is only being configured. Moving the check back
ahead of the handshake makes VK's «Подтвердить» fail while the API answers `401`, which is the
failure this file exists to prevent.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from onboarding.api.app import create_app
from onboarding.app.settings import Settings

CONFIRMATION_CODE = "8af44b85"
VK_SECRET = "vk-secret"
TELEGRAM_SECRET = "tg-secret"


def _client(channels: str = "vk,telegram") -> TestClient:
    return TestClient(
        create_app(
            Settings(
                _env_file=None,
                admin_tokens_raw="token:hr_admin:hr-1",
                channels_raw=channels,
                telegram_webhook_secret=TELEGRAM_SECRET,
                vk_webhook_secret=VK_SECRET,
                vk_confirmation_code=CONFIRMATION_CODE,
            )
        )
    )


@pytest.mark.parametrize("secret", [None, "", "not-the-real-secret"])
def test_vk_confirmation_is_answered_without_a_secret(secret: str | None) -> None:
    payload: dict[str, object] = {"type": "confirmation", "group_id": 242545422}
    if secret is not None:
        payload["secret"] = secret

    with _client() as http:
        response = http.post("/webhook/vk", json=payload)

    assert response.status_code == 200
    assert response.text == CONFIRMATION_CODE


def test_the_confirmation_body_is_not_a_credential() -> None:
    """The move is safe only because the answer VK asks for is public: VK shows it in its UI."""
    with _client() as http:
        answered = http.post("/webhook/vk", json={"type": "confirmation"})
        rejected = http.post(
            "/webhook/vk",
            json={
                "type": "message_new",
                "group_id": 242545422,
                "event_id": "e1",
                "object": {"message": {"from_id": 1, "peer_id": 1, "text": "/start"}},
            },
        )

    assert answered.text == CONFIRMATION_CODE
    assert rejected.status_code == 401


def test_a_vk_body_that_cannot_carry_the_secret_is_refused() -> None:
    with _client() as http:
        response = http.post("/webhook/vk", content=b"{not json")

    assert response.status_code == 401


def test_a_telegram_body_that_is_not_json_is_named_as_such() -> None:
    """Telegram authenticates in a header, so the body is reachable and the refusal is a 400."""
    with _client() as http:
        response = http.post(
            "/webhook/telegram",
            content=b"{not json",
            headers={"X-Telegram-Bot-Api-Secret-Token": TELEGRAM_SECRET},
        )

    assert response.status_code == 400


def test_the_handshake_does_not_open_a_channel_that_is_off() -> None:
    with _client("telegram") as http:
        response = http.post("/webhook/vk", json={"type": "confirmation"})

    assert response.status_code == 404
