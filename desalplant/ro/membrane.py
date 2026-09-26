"""A single membrane element inside the train."""

from ..ns.alarm import Alarm, Severity, make_alarm
from .alarm import MembraneAlarm


class Membrane:
    """Membrane element whose flow gates the pressure ramp."""

    def __init__(self, flow: float, min_flow: float) -> None:
        self.flow = float(flow)
        self.min_flow = float(min_flow)
        self.cracked = False
        self.pressurized = False

    def pressurize(self, pressure: float) -> None:
        """Pressurise the element, cracking it when the flow was too low."""
        self.pressurized = True
        if pressure > 0 and self.flow < self.min_flow:
            self.cracked = True

    def recovery(self, feed: float) -> float:
        """Recovery percentage of the element against a feed flow."""
        if feed <= 0:
            return 0.0
        return self.flow / feed * 100

    def needs_clean(self, differential: float, limit: float) -> bool:
        """Whether the pressure differential calls for a clean."""
        return differential > limit

    def alarm(self) -> Alarm:
        """Current alarm for the element."""
        if self.cracked:
            return make_alarm(Severity.CRITICAL, "membrane cracked")
        if self.flow < self.min_flow:
            return make_alarm(Severity.WARNING, "membrane flow not ready")
        return make_alarm(Severity.INFO, "membrane normal")

    def status(self) -> MembraneAlarm:
        """Structured condition of the element."""
        return MembraneAlarm(
            cracked=self.cracked,
            fouled=self.pressurized and self.flow < self.min_flow,
        )

    def __str__(self) -> str:
        return f"flow={self.flow:.1f} min={self.min_flow:.1f} cracked={self.cracked}"
