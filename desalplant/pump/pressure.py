"""Brine-gated pressure ramp."""

from ..brine.valve import ValveGate
from .state import Pump


def ramp_pressure(pump: Pump, valve, target: float) -> float:
    """Open the brine path first, then establish pressure."""
    gate = ValveGate()
    gate.open(valve)
    gate.require_ready()
    pump.set_pressure(target)
    valve.pressurize(target)
    return pump.pressure
