"""Failures the file intake understands.

They live apart from the intake so a messenger adapter can raise one without importing the database
layer, and so the worker can catch exactly these.
"""

from __future__ import annotations


class FileTooLargeError(ValueError):
    """The attachment is bigger than the deployment allows."""


class FileNotAvailableError(ValueError):
    """The messenger gave no way to download this attachment."""
