"""Render a versioned prompt template.

Placeholders are ``{{name}}``. Both a missing value and an unused value are errors: the first sends
an empty context to the model, the second hides a typo in the template.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

_PLACEHOLDER = re.compile(r"\{\{\s*([a-z][a-z0-9_]*)\s*\}\}")


class PromptError(ValueError):
    """A prompt template and its values do not match."""


def placeholders(template: str) -> tuple[str, ...]:
    return tuple(_PLACEHOLDER.findall(template))


def render(template: str, values: Mapping[str, str]) -> str:
    expected = set(placeholders(template))
    given = set(values)
    missing = sorted(expected - given)
    if missing:
        raise PromptError(f"missing prompt values: {missing}")
    unused = sorted(given - expected)
    if unused:
        raise PromptError(f"unused prompt values: {unused}")
    return _PLACEHOLDER.sub(lambda match: values[match.group(1)], template)
