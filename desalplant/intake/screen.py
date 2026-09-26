"""Intake screen whose head loss flags fouling."""

from dataclasses import dataclass


@dataclass
class Screen:
    """Screen that reports the difference between its two sides."""

    delta: float = 0.0

    def measure(self, upstream: float, downstream: float) -> float:
        """Record the head loss across the screen."""
        self.delta = upstream - downstream
        return self.delta

    def fouled(self, limit: float) -> bool:
        """True when the head loss exceeds the cleaning limit."""
        return self.delta > limit

    def clear(self) -> None:
        """Reset the head loss after a cleaning pass."""
        self.delta = 0.0
