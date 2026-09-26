"""Backwash scheduling for the media bed."""

from dataclasses import dataclass

DEFAULT_INTERVAL = 300


@dataclass(frozen=True)
class BackwashSchedule:
    """Interval in ticks between two backwashes."""

    interval: int
    last: int

    def due(self, now: int) -> bool:
        """True once the interval has elapsed since the last backwash."""
        return now - self.last >= self.interval


def schedule(now: int, interval: int = DEFAULT_INTERVAL) -> BackwashSchedule:
    """Start a fresh backwash schedule at ``now``."""
    return BackwashSchedule(interval=interval, last=now)
