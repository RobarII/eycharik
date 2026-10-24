"""TLS trust for the messengers and the providers.

MAX anchors its API chain at the Russian Trusted Root CA, but its media host (``iu.oneme.ru``)
serves a public Let's Encrypt certificate. A single custom bundle therefore has to carry both
roots: pointing ``httpx`` straight at the Russian bundle alone fails the image upload with
``CERTIFICATE_VERIFY_FAILED``.

``MAX_CA_BUNDLE`` adds its certificates to the default store instead of replacing it, so the
Russian bundle works as is and a merged system bundle keeps working too.
"""

from __future__ import annotations

import ssl
from pathlib import Path


def verify(ca_bundle: Path | None) -> bool | ssl.SSLContext:
    """Return what ``httpx`` should verify against: the default store, plus the extra bundle."""
    if ca_bundle is None:
        return True
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=str(ca_bundle))
    return context
