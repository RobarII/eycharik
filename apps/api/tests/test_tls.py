"""The extra CA bundle extends the default trust store; it does not replace it."""

from __future__ import annotations

import ssl
from pathlib import Path

from onboarding.app.tls import verify

RUSSIAN_CA = Path(__file__).resolve().parents[3] / "infra" / "certs" / "russian_trusted_ca.crt"


def test_no_bundle_keeps_the_default_store() -> None:
    assert verify(None) is True


def test_bundle_adds_roots_to_the_default_store() -> None:
    baseline = ssl.create_default_context().cert_store_stats()["x509_ca"]
    context = verify(RUSSIAN_CA)
    assert isinstance(context, ssl.SSLContext)
    assert context.cert_store_stats()["x509_ca"] >= baseline + 1


def test_context_still_trusts_public_hosts() -> None:
    """MAX media lives on a Let's Encrypt certificate while the API uses the Russian root."""
    context = verify(RUSSIAN_CA)
    assert isinstance(context, ssl.SSLContext)
    issuers = {str(cert["issuer"]) for cert in context.get_ca_certs()}
    assert any("ISRG" in issuer or "Encrypt" in issuer for issuer in issuers)
    assert any("Russian Trusted" in issuer for issuer in issuers)
