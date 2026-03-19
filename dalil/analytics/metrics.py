"""
Metrics stubs — counters and histograms that can later connect to
Prometheus, Grafana, Datadog, etc.

For now, tracks in-memory counters. Production deployment would replace
these with prometheus_client or similar.
"""

from __future__ import annotations

import threading
from collections import defaultdict


class MetricsCollector:
    """Thread-safe in-memory metrics collector."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, int] = defaultdict(int)
        self._histograms: dict[str, list[float]] = defaultdict(list)

    def increment(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] += value

    def observe(self, name: str, value: float) -> None:
        """Record an observation (e.g., latency)."""
        with self._lock:
            self._histograms[name].append(value)

    def get_counter(self, name: str) -> int:
        with self._lock:
            return self._counters[name]

    def get_histogram_stats(self, name: str) -> dict[str, float]:
        with self._lock:
            values = self._histograms.get(name, [])
        if not values:
            return {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0}
        return {
            "count": len(values),
            "mean": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }

    def snapshot(self) -> dict:
        """Return a snapshot of all metrics."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "histograms": {
                    k: self.get_histogram_stats(k)
                    for k in self._histograms
                },
            }


# Global singleton
metrics = MetricsCollector()
