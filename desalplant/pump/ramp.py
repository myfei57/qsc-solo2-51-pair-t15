"""Flow-gated pressure ramp across the pump and the membrane train."""

import math
from dataclasses import dataclass

from ..errors import FlowNotReadyError, MembraneCrackedError
from ..ro.flow import FlowGate
from ..ro.membrane import Membrane
from .state import Pump


@dataclass(frozen=True)
class RampProfile:
    """Start, end and step of a stepped pressure ramp."""

    start: float
    end: float
    step: float

    def steps(self) -> int:
        """Number of steps the ramp needs to reach its end value."""
        if self.step <= 0:
            return 1
        return max(int(math.ceil((self.end - self.start) / self.step)), 1)


def apply_profile(pump: Pump, profile: RampProfile) -> float:
    """Walk a stepped ramp and adopt the resulting pressure."""
    if profile.step <= 0:
        return profile.end
    current = profile.start
    while current < profile.end:
        current = min(current + profile.step, profile.end)
    pump.set_pressure(current)
    return current


def ramp(pump: Pump, membrane: Membrane, target: float) -> float:
    """Pressurise only after the membrane flow was confirmed."""
    gate = FlowGate(membrane.min_flow)
    gate.confirm(membrane.flow)
    if target <= 0:
        raise FlowNotReadyError("membrane flow not confirmed")
    pump.set_pressure(target)
    membrane.pressurize(target)
    if membrane.cracked:
        raise MembraneCrackedError("membrane cracked during pressure ramp")
    return pump.pressure
