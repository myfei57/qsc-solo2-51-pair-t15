"""Pressure interlock that keeps the intake gate shut on a live line."""

from dataclasses import dataclass

LIVE_PRESSURE = 40.0


@dataclass
class GateInterlock:
    """Blocks gate movement while the downstream train is pressurised."""

    enabled: bool = True

    def can_open(self, pressure: float) -> bool:
        """True when the gate may open at the measured pressure."""
        if self.enabled and pressure > LIVE_PRESSURE:
            return False
        return True
