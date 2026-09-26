"""Brine stream fed by the pump pressure."""

from dataclasses import dataclass

from . import stream_calc
from .telemetry import StreamTelemetry


@dataclass
class BrineStream:
    """Concentrate stream with its salinity fraction."""

    concentration: float = 0.6

    def recover(self, flow: float) -> float:
        """Share of the combined stream carried by the permeate."""
        return stream_calc.concentration_ratio(flow, self.concentration)

    def emergency_flow(self) -> float:
        """Flush flow used while the discharge is in emergency."""
        return self.concentration * 3

    def reject_flow(self, feed: float) -> float:
        """Concentrate flow for a feed flow."""
        return stream_calc.reject_flow(self.concentration, feed)

    def recovery_rate(self, feed: float) -> float:
        """Recovery fraction for a feed flow."""
        return stream_calc.recovery_rate(self.concentration, feed)

    def disposal_volume(self, feed: float, hours: float) -> float:
        """Concentrate volume produced over a number of hours."""
        return stream_calc.disposal_volume(self.concentration, feed, hours)

    def collect(self, flow: float) -> StreamTelemetry:
        """Capture a stream sweep."""
        return StreamTelemetry(flow=flow, concentration=self.concentration)
