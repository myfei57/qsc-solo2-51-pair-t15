"""Summary over the curves, stream arithmetic and membranes."""

from typing import TYPE_CHECKING, Any

from ..pump.curve_builder import build_curve

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for type checkers
    from .plant import Plant

CURVE_POINTS = ((20.0, 14.0), (50.0, 38.0), (80.0, 62.0))
SUMMARY_FEED = 80.0
SUMMARY_HOURS = 24.0
INTAKE_SPEED = 100.0
INTAKE_LEVEL = 60.0
REQUIRED_FLOW = 70.0
DIFFERENTIAL = 18.0
DIFFERENTIAL_LIMIT = 20.0


def build_summary(plant: "Plant") -> dict[str, Any]:
    """Summarise the curve range, stream flows and membrane condition."""
    curve = build_curve(CURVE_POINTS)
    alarm = plant.membrane.alarm()
    status = plant.membrane.status()
    return {
        "curve_span": curve.span(),
        "curve_min_power": curve.min_power(),
        "curve_max_power": curve.max_power(),
        "reject_flow": plant.brine_stream.reject_flow(SUMMARY_FEED),
        "recovery_rate": plant.brine_stream.recovery_rate(SUMMARY_FEED),
        "disposal_volume": plant.brine_stream.disposal_volume(SUMMARY_FEED, SUMMARY_HOURS),
        "intake_flow": plant.intake_pump.flow_rate(INTAKE_SPEED),
        "target_flow": plant.intake_pump.target_flow(INTAKE_LEVEL),
        "feed_available": plant.feed.available(REQUIRED_FLOW),
        "membrane_alarm": alarm.to_dict(),
        "needs_clean": plant.membrane.needs_clean(DIFFERENTIAL, DIFFERENTIAL_LIMIT),
        "membrane_status": status.to_dict(),
    }
