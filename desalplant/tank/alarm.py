"""Product tank level alarm."""

from ..ns.alarm import Alarm, Severity, make_alarm
from .level import Level

HIGH_LEVEL = 90.0
LOW_LEVEL = 10.0


def level_alarm(level: Level) -> Alarm:
    """Current alarm for the product level."""
    if level.percent >= HIGH_LEVEL:
        return make_alarm(Severity.WARNING, "tank level high")
    if level.percent <= LOW_LEVEL:
        return make_alarm(Severity.CRITICAL, "tank level low")
    return make_alarm(Severity.INFO, "tank level normal")
