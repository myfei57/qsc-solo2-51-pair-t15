"""One pump sweep and the efficiency it implies."""

from dataclasses import dataclass
from typing import Any

from .state import Pump


@dataclass(frozen=True)
class Telemetry:
    """Pressure, flow and power captured in one sweep."""

    pressure: float
    flow: float
    power: float

    def efficiency(self) -> float:
        """Flow produced per unit of power."""
        if self.power <= 0:
            return 0.0
        return self.flow / self.power

    def to_dict(self) -> dict[str, Any]:
        return {"pressure": self.pressure, "flow": self.flow, "power": self.power}


def collect(pump: Pump, power: float, flow: float) -> Telemetry:
    """Capture a pump sweep at the pump's current pressure."""
    return Telemetry(pressure=pump.pressure, flow=flow, power=power)
