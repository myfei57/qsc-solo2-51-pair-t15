"""Pump alarm derived from its supply and pressure."""

from ..ns.alarm import Alarm, Severity, make_alarm
from .state import Pump

HIGH_PRESSURE = 70.0


def pump_alarm(pump: Pump) -> Alarm:
    """Current alarm for the pump."""
    if pump.stalled:
        return make_alarm(Severity.CRITICAL, "pump supply stalled")
    if pump.pressure > HIGH_PRESSURE:
        return make_alarm(Severity.WARNING, "pump pressure high")
    return make_alarm(Severity.INFO, "pump normal")
