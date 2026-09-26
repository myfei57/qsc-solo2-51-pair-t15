"""Brine valve that has to be open before the pump ramps."""

from ..errors import ValveNotOpenError


class Valve:
    """Discharge valve with an emergency and a stress flag."""

    def __init__(self, stuck: bool = False) -> None:
        self.open = False
        self.emergency = False
        self.stressed = False
        self.stuck = stuck

    def open_valve(self) -> None:
        """Open the valve; a stuck actuator leaves the outlet shut."""
        if not self.stuck:
            self.open = True

    def close_valve(self) -> None:
        """Close the valve."""
        self.open = False

    def pressurize(self, pressure: float) -> None:
        """Pressurise the housing, flagging stress when the outlet is shut."""
        if pressure > 0 and not self.open:
            self.stressed = True

    def set_emergency(self) -> None:
        """Put the valve into its emergency position."""
        self.emergency = True

    def release_emergency(self) -> None:
        """Leave the emergency position."""
        self.emergency = False


class ValveGate:
    """Confirms the brine path is open."""

    def __init__(self) -> None:
        self._open = False

    def open(self, valve: Valve) -> None:
        """Open the valve and remember whether the path really opened."""
        valve.open_valve()
        self._open = valve.open

    def ready(self) -> bool:
        """Whether the path is open."""
        return self._open

    def require_ready(self) -> None:
        """Raise unless the path is open."""
        if not self._open:
            raise ValveNotOpenError("brine valve not open")
