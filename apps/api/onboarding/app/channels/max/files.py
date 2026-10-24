"""Download an attachment MAX already accepted.

MAX hands out a URL per attachment. It is fetched from the worker, chunk by chunk, with the size cap
enforced before the body is buffered: a messenger that advertises a 2 KB file and streams 2 GB must
not be able to exhaust memory.

The bot token is attached only for MAX's own host. A CDN URL signed by the platform does not expect
an Authorization header, and sending a secret to a host the messenger named is how a token leaks.
"""

from __future__ import annotations

from urllib.parse import urlsplit

import httpx
from pydantic import SecretStr

from onboarding.app.files.errors import FileTooLargeError
from onboarding.ports import InboundFile


class FileFetchError(RuntimeError):
    """MAX did not return the bytes. The message never contains the URL's signature."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)


class MaxFiles:
    """The ``FileFetcher`` port for MAX."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        token: SecretStr,
        platform_host: str,
        max_bytes: int,
    ) -> None:
        self._client = client
        self._token = token
        self._platform_host = platform_host
        self._max_bytes = max_bytes

    async def fetch(self, file: InboundFile) -> bytes:
        if file.url is None:
            raise FileFetchError("no_url")
        headers = {}
        if urlsplit(file.url).hostname == self._platform_host:
            headers["Authorization"] = self._token.get_secret_value()
        try:
            async with self._client.stream("GET", file.url, headers=headers) as response:
                if response.status_code != httpx.codes.OK:
                    raise FileFetchError(f"status_{response.status_code}")
                declared = response.headers.get("content-length", "")
                if declared.isdigit() and int(declared) > self._max_bytes:
                    raise FileTooLargeError("content_length")
                buffer = bytearray()
                async for chunk in response.aiter_bytes():
                    buffer.extend(chunk)
                    if len(buffer) > self._max_bytes:
                        raise FileTooLargeError("streamed")
        except httpx.HTTPError as error:
            raise FileFetchError(type(error).__name__) from error
        return bytes(buffer)
