"""Linear interpolation along the efficiency curve."""

from .curve_set import EfficiencyCurve
from .state import Pump


def interpolate(curve: EfficiencyCurve, power: float) -> float:
    """Flow expected at an arbitrary power, clamped to the curve ends."""
    points = curve.points
    if not points:
        return 0.0
    if power <= points[0].power:
        return points[0].flow
    for index in range(1, len(points)):
        left = points[index - 1]
        right = points[index]
        if power <= right.power:
            ratio = (power - left.power) / (right.power - left.power)
            return left.flow + ratio * (right.flow - left.flow)
    return points[-1].flow


def fitted_flow(pump: Pump, curve: EfficiencyCurve, power: float) -> float:
    """Flow the pump is expected to deliver at a power draw."""
    return interpolate(curve, power)
