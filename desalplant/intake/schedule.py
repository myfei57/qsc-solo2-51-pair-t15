"""Cleaning schedule for the intake screen."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CleanSchedule:
    """Interval in ticks between two screen cleaning passes."""

    interval: int
    last: int

    def due(self, now: int) -> bool:
        """True once the interval has elapsed since the last pass."""
        return now - self.last >= self.interval

    def next_due(self) -> int:
        """Tick at which the next pass becomes due."""
        return self.last + self.interval
