"""Permeate batch used for yield and blending arithmetic."""

from dataclasses import dataclass, replace
from typing import Any


@dataclass(frozen=True)
class Batch:
    """A quantity of permeate with its conductivity."""

    id: str
    permeate: float
    conductivity: float

    def acceptable(self, max_cond: float) -> bool:
        """Whether the batch stays inside a conductivity limit."""
        return self.conductivity <= max_cond

    def yield_percent(self, feed: float) -> float:
        """Batch yield as a percentage of the feed."""
        if feed <= 0:
            return 0.0
        return self.permeate / feed * 100

    def blend(self, other: "Batch", weight: float) -> "Batch":
        """Blend this batch with another; ``weight`` is clamped to [0, 1]."""
        clamped = min(max(weight, 0.0), 1.0)
        return replace(
            self,
            id=f"{self.id}+{other.id}",
            permeate=self.permeate * (1 - clamped) + other.permeate * clamped,
            conductivity=self.conductivity * (1 - clamped) + other.conductivity * clamped,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "permeate": self.permeate,
            "conductivity": self.conductivity,
        }
