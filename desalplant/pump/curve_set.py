"""Efficiency curve expressed as power and flow points."""

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class CurvePoint:
    """One power/flow pair of the efficiency curve."""

    power: float
    flow: float


@dataclass(frozen=True)
class EfficiencyCurve:
    """Ordered curve points used for interpolation."""

    points: tuple[CurvePoint, ...]

    def flow_at(self, power: float) -> float:
        """Last flow point at or below ``power``."""
        if not self.points:
            return 0.0
        flow = self.points[0].flow
        for point in self.points:
            if point.power <= power:
                flow = point.flow
            else:
                break
        return flow

    def min_power(self) -> float:
        """Lowest power on the curve."""
        if not self.points:
            return 0.0
        return min(point.power for point in self.points)

    def max_power(self) -> float:
        """Highest power on the curve."""
        if not self.points:
            return 0.0
        return max(point.power for point in self.points)

    def span(self) -> float:
        """Width of the curve's power range."""
        return self.max_power() - self.min_power()


def new_curve(points: Iterable[CurvePoint]) -> EfficiencyCurve:
    """Build a curve, requiring strictly increasing power across the points."""
    collected = tuple(points)
    previous = float("-inf")
    for point in collected:
        if point.power <= previous:
            raise ValueError("curve points must ascend in power")
        previous = point.power
    return EfficiencyCurve(points=collected)
