"""Small pump commands shared by the console operations."""

from .state import Pump


def hold(pump: Pump, pressure: float) -> bool:
    """Hold the pump at a pressure."""
    return pump.hold(pressure)


def idle(pump: Pump) -> Pump:
    """Return the pump to idle and hand it back."""
    pump.idle()
    return pump
