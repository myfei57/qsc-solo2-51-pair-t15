"""Permeate stream, its conductivity latch and rejection volume."""

from dataclasses import dataclass
from typing import Any

from .quality import PermeateGrade


@dataclass(frozen=True)
class PermeateStats:
    """Flow and rejected volume captured in one sweep."""

    flow_rate: float
    rejected_volume: float

    def to_dict(self) -> dict[str, Any]:
        return {"flow_rate": self.flow_rate, "rejected_volume": self.rejected_volume}


class Permeate:
    """Permeate stream that stays latched until the conductivity recovers."""

    def __init__(self, max_cond: float) -> None:
        self.conductivity = 0.0
        self.max_cond = float(max_cond)
        self.rejecting = True
        self._recovered = False

    def update_conductivity(self, conductivity: float) -> bool:
        """Record a conductivity reading and update the rejection latch."""
        self.conductivity = float(conductivity)
        if conductivity <= self.max_cond:
            self.rejecting = False
            self._recovered = True
        else:
            self.rejecting = True
            self._recovered = False
        return self._recovered

    def recovered(self) -> bool:
        """Whether the stream has cleared its rejection latch."""
        return self._recovered

    def rejecting_now(self) -> bool:
        """Whether the stream is currently rejected."""
        return self.rejecting

    def conductivity_normal(self) -> bool:
        """Whether the last conductivity stayed inside the limit."""
        return self.conductivity <= self.max_cond

    def grade(self) -> PermeateGrade:
        """Quality grade of the stream."""
        return PermeateGrade.from_conductivity(self.conductivity, self.max_cond)

    def safe(self, max_cond: float) -> bool:
        """Whether the stream is safe against an explicit limit."""
        return self.conductivity <= max_cond

    def measure_flow(self, flow: float) -> PermeateStats:
        """Capture a flow reading, counting it as rejected while latched."""
        rejected = flow if self.rejecting else 0.0
        return PermeateStats(flow_rate=flow, rejected_volume=rejected)

    def reject_volume(self, flow: float) -> float:
        """Volume that has to be dumped for a given flow while latched."""
        if self.rejecting:
            return flow
        return 0.0
