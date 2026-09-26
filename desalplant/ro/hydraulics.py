"""Hydraulic quantities reported for the membrane train."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Flux:
    """Permeate flow spread over a membrane area."""

    permeate: float
    area: float

    def lmh(self) -> float:
        """Flux in litres per square metre per hour."""
        if self.area <= 0:
            return 0.0
        return self.permeate / self.area

    def to_dict(self) -> dict[str, Any]:
        return {"permeate": self.permeate, "area": self.area, "lmh": self.lmh()}


@dataclass(frozen=True)
class PressureVessel:
    """Element load inside one pressure vessel."""

    elements: int
    active: int

    def packed(self) -> float:
        """Fraction of the vessel that is loaded."""
        if self.elements == 0:
            return 0.0
        return self.active / self.elements

    def dead_end(self) -> bool:
        """True when the vessel carries no active element."""
        return self.active == 0


@dataclass(frozen=True)
class ConcentrationPolarization:
    """Brine-to-feed concentration ratio at the membrane surface."""

    feed: float
    brine: float

    def factor(self) -> float:
        """Polarization factor."""
        if self.feed <= 0:
            return 0.0
        return self.brine / self.feed
