"""Admissible level band for a product tank."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LevelBand:
    """Lower and upper level bounds."""

    low: float
    high: float

    def __post_init__(self) -> None:
        if self.low > self.high:
            raise ValueError("level band lower bound exceeds the upper bound")

    def contains(self, value: float) -> bool:
        """Whether a level sits inside the band."""
        return self.low <= value <= self.high
