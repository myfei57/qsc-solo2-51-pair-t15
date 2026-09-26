"""Telemetry and diagnostics sweeps for the console."""

from typing import TYPE_CHECKING, Any

from ..ns.telemetry import Telemetry
from ..pump.curve_set import CurvePoint, new_curve
from ..ro.flow import FlowCheck, FlowGate

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for type checkers
    from .plant import Plant

SCREEN_UPSTREAM = 96.0
SCREEN_DOWNSTREAM = 82.0
OPERATING_POWER = 60.0
PERMEATE_FLOW = 52.0


def telemetry(plant: "Plant") -> Telemetry:
    """One sweep across the feed, screen, brine and permeate paths."""
    sweep = Telemetry()
    check = FlowCheck()
    sweep.add("feed_flow", check.measure(plant.membrane))
    plant.screen.measure(SCREEN_UPSTREAM, SCREEN_DOWNSTREAM)
    sweep.add("screen_delta", plant.screen.delta)
    sweep.add("brine_recovery", plant.brine_stream.recover(plant.hp_pump.pressure))
    curve = new_curve(
        [
            CurvePoint(power=20.0, flow=14.0),
            CurvePoint(power=50.0, flow=38.0),
            CurvePoint(power=80.0, flow=62.0),
        ]
    )
    sweep.add("operating_flow", curve.flow_at(OPERATING_POWER))
    sweep.add("permeate_flow", plant.permeate.measure_flow(PERMEATE_FLOW).flow_rate)
    sweep.add("supply", plant.hp_pump.supply)
    return sweep


def diagnostics(plant: "Plant") -> dict[str, Any]:
    """Structural readings used to reason about the line."""
    flow_gate = FlowGate(plant.membrane.min_flow)
    return {
        "backwash_pressure_drop": plant.media.pressure_drop(80.0),
        "rack": plant.rack.inspect().to_dict(),
        "array_sensors": plant.array.sensors(),
        "recovery_rate": plant.recovery.rate(),
        "gate_can_open": plant.interlock.can_open(plant.hp_pump.pressure),
        "flow_ready": flow_gate.satisfied(plant.membrane.flow),
        "differential": plant.pump_differential(),
    }
