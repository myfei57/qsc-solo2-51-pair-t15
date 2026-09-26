"""Pump run records used for specific energy arithmetic."""

from dataclasses import dataclass
from typing import Any

from .state import Pump


@dataclass(frozen=True)
class RunRecord:
    """One run of the pump at a pressure and flow."""

    pressure: float
    flow: float

    def specific_energy(self) -> float:
        """Pressure per unit of flow."""
        if self.flow <= 0:
            return 0.0
        return self.pressure / self.flow

    def stable(self, tolerance: float) -> bool:
        """Whether the run flow stayed above the tolerance."""
        return self.flow > tolerance

    def to_dict(self) -> dict[str, Any]:
        return {"pressure": self.pressure, "flow": self.flow}


def record_run(pump: Pump, pressure: float, flow: float) -> RunRecord:
    """Record a run and adopt its pressure."""
    pump.set_pressure(pressure)
    return RunRecord(pressure=pressure, flow=flow)
