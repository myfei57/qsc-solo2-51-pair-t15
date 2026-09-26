"""State of the high pressure pump."""

from ..errors import InvalidEfficiencyError


class Pump:
    """High pressure pump that gates the membrane train."""

    def __init__(self, efficiency: float = 1.0) -> None:
        self.running = False
        self.stopped = False
        self.pressure = 0.0
        self.supply = 0.0
        self.stalled = False
        self.efficiency = efficiency
        self.trip_reason = ""

    def start(self) -> None:
        """Mark the pump as running."""
        self.running = True
        self.stopped = False

    def set_pressure(self, pressure: float) -> None:
        """Adopt a pressure set point."""
        self.pressure = float(pressure)

    def hold(self, pressure: float) -> bool:
        """Hold a positive pressure; a non-positive set point is refused."""
        if pressure <= 0:
            return False
        self.pressure = float(pressure)
        return True

    def trip(self, reason: str) -> None:
        """Trip the pump and record why."""
        self.trip_reason = reason
        self.running = False
        self.stopped = True

    def idle(self) -> None:
        """Return the pump to its idle state."""
        self.running = False
        self.stopped = True
        self.pressure = 0.0

    def recalibrate(self, factor: float) -> float:
        """Adopt a new efficiency factor inside the admissible band."""
        if factor <= 0 or factor > 1:
            raise InvalidEfficiencyError("efficiency factor out of range")
        self.efficiency = float(factor)
        return self.efficiency

    def track_supply(self, open_tanks: int) -> int:
        """Record how many tanks are open and stall on an empty supply."""
        self.supply = float(open_tanks)
        if open_tanks == 0:
            self.stalled = True
        return open_tanks

    def reset_stall(self) -> None:
        """Clear a supply stall."""
        self.stalled = False


def new() -> Pump:
    """Build a pump with its nominal efficiency baseline."""
    return Pump(efficiency=1.0)
