"""Recovery control positions for the brine valve."""

from dataclasses import dataclass

from .limit import RecoveryLimit
from .valve import Valve

CLOSED_RECOVERY = 45.0


@dataclass(frozen=True)
class RecoveryTarget:
    """Set point and measured recovery of the stream."""

    setpoint: float
    actual: float

    def deviation(self) -> float:
        """Measured recovery minus the set point."""
        return self.actual - self.setpoint

    def within(self, tolerance: float) -> bool:
        """Whether the deviation sits inside a tolerance band."""
        return abs(self.deviation()) <= tolerance


def position_for(valve: Valve, recovery: float) -> str:
    """Valve position demanded by a raw recovery figure."""
    if valve.emergency:
        return "emergency"
    if recovery >= CLOSED_RECOVERY:
        return "closed"
    return "open"


def recovery_position(valve: Valve, recovery: float, limit: RecoveryLimit) -> str:
    """Valve position demanded by a clamped recovery figure."""
    clamped = limit.clamp(recovery)
    if valve.emergency:
        return "emergency"
    if clamped >= limit.max:
        return "throttled"
    return "open"
