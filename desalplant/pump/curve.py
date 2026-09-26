"""Pump efficiency baseline."""

from .state import Pump


def recalibrate(pump: Pump, factor: float) -> float:
    """Adopt a fresh efficiency factor."""
    return pump.recalibrate(factor)


def efficiency(pump: Pump) -> float:
    """Current efficiency factor."""
    return pump.efficiency
