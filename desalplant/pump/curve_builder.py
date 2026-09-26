"""Curve construction from raw coordinate pairs."""

from typing import Iterable, Sequence

from .curve_set import CurvePoint, EfficiencyCurve, new_curve


def build_curve(points: Iterable[Sequence[float]]) -> EfficiencyCurve:
    """Build a curve from ``(power, flow)`` pairs."""
    return new_curve(CurvePoint(power=pair[0], flow=pair[1]) for pair in points)
