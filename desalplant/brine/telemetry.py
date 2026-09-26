"""Brine sweep reported alongside the pump telemetry."""

from dataclasses import dataclass
from typing import Any

from .stream_calc import concentration_ratio


@dataclass(frozen=True)
class StreamTelemetry:
    """Flow and salinity captured in one sweep."""

    flow: float
    concentration: float

    def recovery(self) -> float:
        """Share of the combined stream carried by the permeate."""
        return concentration_ratio(self.flow, self.concentration)

    def to_dict(self) -> dict[str, Any]:
        return {"flow": self.flow, "concentration": self.concentration}
