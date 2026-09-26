"""Dose rate set point."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DoseRate:
    """Antiscalant concentration in parts per million."""

    ppm: float

    def __post_init__(self) -> None:
        if self.ppm < 0:
            raise ValueError("dose rate must not be negative")

    def scaled(self, factor: float) -> "DoseRate":
        """A dose rate scaled by a factor."""
        return DoseRate(ppm=self.ppm * factor)
