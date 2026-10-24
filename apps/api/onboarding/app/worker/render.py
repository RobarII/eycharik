"""Turn a verified answer into the message the employee reads.

The answer body keeps the words the model wrote; the source line replaces the internal
``[doc#chunk]`` markers, which stay in the audit trail and the question log only.
"""

from __future__ import annotations

from collections.abc import Sequence

from onboarding.app.copy import Copy
from onboarding.core.grounding import strip_citations

# One or two sources are enough for a chat answer: a longer footer reads as a bibliography.
MAX_SOURCE_NAMES = 2


def render_answer(answer: str, titles: Sequence[str], copy: Copy) -> str:
    body = strip_citations(answer)
    line = copy.source_line(tuple(titles)[:MAX_SOURCE_NAMES])
    return f"{body}\n\n{line}" if line else body
