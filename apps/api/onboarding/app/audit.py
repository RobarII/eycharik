"""Audit port default: do nothing.

The real implementation writes an append-only table. Tests and local runs use this one so an
adapter never needs a database to be importable.
"""

from __future__ import annotations


class NullAudit:
    async def record(self, name: str, **fields: object) -> None:
        del name, fields
