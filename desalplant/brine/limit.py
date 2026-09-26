"""Admissible band for the recovery set point."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RecoveryLimit:
    """Lower and upper recovery bounds."""

    min: float
    max: float

    def __post_init__(self) -> None:
        if self.min > self.max:
            raise ValueError("recovery limit lower bound exceeds the upper bound")

    def clamp(self, value: float) -> float:
        """Pull a value into the band."""
        if value < self.min:
            return self.min
        if value > self.max:
            return self.max
        return value

    def contains(self, value: float) -> bool:
        """Whether a value already sits inside the band."""
        return self.min <= value <= self.max
