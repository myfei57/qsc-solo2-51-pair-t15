"""Small in-process metric registry.

Counters, gauges and rolling samples are kept per name so that a report can
expose the numbers without touching the file store.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Metrics:
    """Counters, gauges and samples keyed by metric name."""

    counters: dict[str, int] = field(default_factory=dict)
    gauges: dict[str, float] = field(default_factory=dict)
    samples: dict[str, list[float]] = field(default_factory=dict)

    def inc(self, name: str, delta: int = 1) -> int:
        """Add ``delta`` to a counter and return the new total."""
        self.counters[name] = self.counters.get(name, 0) + delta
        return self.counters[name]

    def set(self, name: str, value: float) -> None:
        """Record the latest value of a gauge."""
        self.gauges[name] = float(value)

    def observe(self, name: str, value: float) -> None:
        """Append one sample to a rolling series."""
        self.samples.setdefault(name, []).append(float(value))

    def get(self, name: str) -> int:
        """Counter value, defaulting to zero."""
        return self.counters.get(name, 0)

    def gauge(self, name: str) -> float:
        """Gauge value, defaulting to zero."""
        return self.gauges.get(name, 0.0)

    def average(self, name: str) -> float:
        """Mean of the samples recorded under a name."""
        values = self.samples.get(name)
        if not values:
            return 0.0
        return sum(values) / len(values)

    def snapshot(self) -> dict[str, Any]:
        """Counters and gauges as a JSON-friendly mapping."""
        return {
            "counters": dict(sorted(self.counters.items())),
            "gauges": dict(sorted(self.gauges.items())),
        }
