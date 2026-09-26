"""Backwash cycle driven by the media bed."""

from dataclasses import dataclass
from typing import Any

from .media import MediaFilter


@dataclass(frozen=True)
class BackwashCycle:
    """Result of starting a backwash."""

    completed: bool
    pressure_drop: float

    def to_dict(self) -> dict[str, Any]:
        return {"completed": self.completed, "pressure_drop": self.pressure_drop}


def start_backwash(bed: MediaFilter, flow: float) -> BackwashCycle:
    """Clear the backwash flag and capture the head loss at the current flow."""
    bed.backwashed = False
    return BackwashCycle(completed=False, pressure_drop=bed.pressure_drop(flow))


def finish_backwash(bed: MediaFilter) -> BackwashCycle:
    """Complete a backwash and report the cleaned head loss."""
    bed.backwash()
    return BackwashCycle(completed=True, pressure_drop=bed.pressure_drop(0.0))
