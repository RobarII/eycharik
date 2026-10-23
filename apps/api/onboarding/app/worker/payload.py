"""Payload validation errors, shared by the dispatcher and the handlers.

A malformed job must fail loudly and be retried or parked, never half-applied.

The error lives on its own so a handler can raise it without importing the dispatcher
and creating a cycle.
"""

from __future__ import annotations


class JobPayloadError(ValueError):
    """The stored payload does not match the job kind."""
