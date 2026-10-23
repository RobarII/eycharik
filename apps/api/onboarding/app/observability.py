"""Process metrics in the Prometheus text format.

The pilot has no metrics backend, and a metrics dependency is not free: it must be installed,
scraped, and kept compatible. This module keeps the first step small and dependency-free. One
process owns its numbers, exactly like the MAX pacing state; a second worker reports its own
counters and the scraper sums them.

Only labels with bounded cardinality are allowed: status codes, stages, outcome reasons. Never an
employee id, a question, or a document title.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Final

LATENCY_BUCKETS: Final = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.0,
    4.0,
    8.0,
    16.0,
)
LabelKey = tuple[tuple[str, str], ...]


@dataclass(slots=True)
class _Histogram:
    buckets: list[int] = field(default_factory=lambda: [0] * len(LATENCY_BUCKETS))
    total: float = 0.0
    count: int = 0


class Metrics:
    """A tiny registry with Prometheus rendering and no third-party dependency."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, LabelKey], float] = {}
        self._histograms: dict[tuple[str, LabelKey], _Histogram] = {}

    def inc(
        self,
        name: str,
        *,
        labels: dict[str, str] | None = None,
        value: float = 1.0,
    ) -> None:
        key = (name, _labels(labels))
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    def observe(
        self,
        name: str,
        value: float,
        *,
        labels: dict[str, str] | None = None,
    ) -> None:
        key = (name, _labels(labels))
        with self._lock:
            histogram = self._histograms.setdefault(key, _Histogram())
            histogram.total += value
            histogram.count += 1
            for index, bound in enumerate(LATENCY_BUCKETS):
                if value <= bound:
                    histogram.buckets[index] += 1

    def render(self) -> str:
        with self._lock:
            counters = sorted(self._counters.items())
            histograms = sorted(self._histograms.items())
        lines: list[str] = []
        declared: set[str] = set()
        for (name, labels), value in counters:
            if name not in declared:
                lines.append(f"# TYPE {name} counter")
                declared.add(name)
            lines.append(f"{name}{_render_labels(labels)} {_number(value)}")
        for (name, labels), histogram in histograms:
            if name not in declared:
                lines.append(f"# TYPE {name} histogram")
                declared.add(name)
            for index, bound in enumerate(LATENCY_BUCKETS):
                bucket_labels = (*labels, ("le", _number(bound)))
                lines.append(
                    f"{name}_bucket{_render_labels(bucket_labels)} {histogram.buckets[index]}"
                )
            infinity = (*labels, ("le", "+Inf"))
            lines.append(f"{name}_bucket{_render_labels(infinity)} {histogram.count}")
            lines.append(f"{name}_sum{_render_labels(labels)} {_number(histogram.total)}")
            lines.append(f"{name}_count{_render_labels(labels)} {histogram.count}")
        return "\n".join(lines) + ("\n" if lines else "")

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._histograms.clear()


def _labels(labels: dict[str, str] | None) -> LabelKey:
    if not labels:
        return ()
    return tuple(sorted((str(key), str(value)) for key, value in labels.items()))


def _render_labels(labels: LabelKey) -> str:
    if not labels:
        return ""
    body = ",".join(f'{key}="{_escape(value)}"' for key, value in labels)
    return "{" + body + "}"


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _number(value: float) -> str:
    return str(int(value)) if value == int(value) else repr(value)


metrics = Metrics()
