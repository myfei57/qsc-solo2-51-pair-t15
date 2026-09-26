"""Dosing schedule."""

from dataclasses import dataclass

from .doser import Doser


@dataclass(frozen=True)
class DoseSchedule:
    """Interval in ticks between two dosing runs."""

    interval: int
    last: int

    def due(self, now: int) -> bool:
        """True once the interval has elapsed since the last run."""
        return now - self.last >= self.interval


def schedule_due(doser: Doser, schedule: DoseSchedule, now: int) -> bool:
    """Whether a scheduled dosing run is due."""
    return schedule.due(now)
