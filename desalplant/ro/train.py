"""Multi-stage membrane train used for hydraulics arithmetic."""

from dataclasses import dataclass

STAGE_DECAY = 0.08


@dataclass(frozen=True)
class Train:
    """Train geometry: number of stages and elements per stage."""

    stages: int
    elements_per_stage: int

    def total_elements(self) -> int:
        """Number of elements in the train."""
        return self.stages * self.elements_per_stage

    def stage_feed(self, flow: float) -> tuple[float, ...]:
        """Feed flow reaching each successive stage."""
        return tuple(flow * (1 - STAGE_DECAY * index) for index in range(self.stages))

    def recovery(self, flow: float, concentrate: float) -> float:
        """Recovery percentage from the feed and concentrate flows."""
        if flow <= 0:
            return 0.0
        return (flow - concentrate) / flow * 100

    def flux(self, permeate: float) -> float:
        """Flux per element for a permeate flow."""
        area = float(self.total_elements())
        if area <= 0:
            return 0.0
        return permeate / area
