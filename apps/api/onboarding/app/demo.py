"""Who may use the demo commands.

An empty list means the whole stand is a demo stand, which keeps local runs and the rehearsal
environment working without configuration (roadmap 1.6). Ids are compared as strings: tests and
fixtures use non-numeric identifiers.
"""

from __future__ import annotations

from collections.abc import Collection

from onboarding.core.models import EmployeeId


def demo_allowed(employee_id: EmployeeId, demo_ids: Collection[object]) -> bool:
    if not demo_ids:
        return True
    return str(employee_id) in {str(candidate) for candidate in demo_ids}
