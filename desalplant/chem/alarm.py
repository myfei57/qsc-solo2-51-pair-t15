"""Chemical tank alarm."""

from ..ns.alarm import Alarm, Severity, make_alarm
from .tank import ChemicalTank

LOW_LEVEL = 10.0


def tank_alarm(tank: ChemicalTank) -> Alarm:
    """Current alarm for the chemical tank."""
    if tank.level <= LOW_LEVEL:
        return make_alarm(Severity.WARNING, "chemical tank level low")
    return make_alarm(Severity.INFO, "chemical tank level normal")
